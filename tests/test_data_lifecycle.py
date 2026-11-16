"""Hard guarantees: raw source is never a write destination."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline import file_sha256, persist_processed_dataset


def _make_source(tmp_path: Path):
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    source = raw / "original.csv"
    source.write_text("Order Id,Sales\n1,10\n2,20\n", encoding="utf-8")
    return source


def _save(tmp_path, source, output_name="cleaned_v1.csv"):
    return persist_processed_dataset(
        pd.DataFrame({"Order Id": [1, 2], "Sales": [10, 20], "flag": [True, False]}),
        source_path=source,
        output_name=output_name,
        transformation_steps=["typed flag; no rows excluded"],
        decision_ids=["D-EXAMPLE"],
        project_root=tmp_path,
    )


def test_processed_csv_is_versioned_and_raw_bytes_are_unchanged(tmp_path):
    original = _make_source(tmp_path)
    before = original.read_bytes()
    old_hash = file_sha256(original)
    processed, provenance = _save(tmp_path, original)
    assert original.read_bytes() == before
    assert file_sha256(original) == old_hash
    assert processed.parent == (tmp_path / "data" / "processed")
    assert processed.exists() and provenance.exists()
    metadata = json.loads(provenance.read_text(encoding="utf-8"))
    assert metadata["source_sha256"] == hashlib.sha256(before).hexdigest()
    assert metadata["processed_sha256"] == file_sha256(processed)
    assert metadata["transformation_steps"] == ["typed flag; no rows excluded"]
    assert metadata["status"] == "STORED_LOCALLY_NOT_PUBLICATION_APPROVED"
    assert metadata["input_rows"] == 2 and metadata["output_rows"] == 2


def test_existing_processed_csv_cannot_be_overwritten(tmp_path):
    source = _make_source(tmp_path)
    first, manifest = _save(tmp_path, source)
    before = first.read_bytes()
    with pytest.raises(FileExistsError):
        _save(tmp_path, source)
    assert first.read_bytes() == before and manifest.exists()


@pytest.mark.parametrize("output_name", ["../raw/original.csv", "/tmp/other.csv", "nested/file.csv", "not_csv.txt"])
def test_processed_output_path_traversal_is_refused(tmp_path, output_name):
    source = _make_source(tmp_path)
    with pytest.raises(ValueError):
        _save(tmp_path, source, output_name=output_name)


def test_input_must_be_from_raw_folder(tmp_path):
    source = _make_source(tmp_path)
    other = tmp_path / "outside.csv"
    other.write_bytes(source.read_bytes())
    with pytest.raises(ValueError):
        _save(tmp_path, other)


def test_metadata_requires_transformation_and_approved_decision(tmp_path):
    source = _make_source(tmp_path)
    for steps, decisions in [([], ["D-001"]), (["typed"], [])]:
        with pytest.raises(ValueError):
            persist_processed_dataset(
                pd.DataFrame({"a": [1]}), source_path=source, output_name="v1.csv",
                transformation_steps=steps, decision_ids=decisions, project_root=tmp_path,
            )


def test_processed_symlink_to_raw_is_refused(tmp_path):
    source = _make_source(tmp_path)
    processed = tmp_path / "data" / "processed"
    try:
        processed.symlink_to(source.parent, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Directory symlinks not available on this platform")
    with pytest.raises(ValueError, match="separate directory"):
        _save(tmp_path, source)
    assert sorted(p.name for p in source.parent.iterdir()) == ["original.csv"]
