"""De publicatiebundel: wat online mag staan, zonder de ruwe CSV (met persoonsgegevens)."""
import json
from pathlib import Path

import pandas as pd
import pytest

import pipeline
from test_dataco_kpis import raw_line

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"
FORBIDDEN = ("customer", "email", "password", "fname", "lname", "street", "zipcode")


def _project_with_tiny_raw(tmp_path):
    """Een klein project met een nagemaakte ruwe CSV (de 13 analysekolommen, latin1 zoals het echte bestand)."""
    rows = [raw_line(1, 1, category="Cleats"), raw_line(1, 2, category="Shoes"),   # één order, twee categorieën, dezelfde status
            raw_line(2, 3, market="LATAM", category="Cleats", status="Shipping on time", total=200.0, profit=-5.0),
            raw_line(3, 4, order_status="CANCELED", status="Shipping canceled"),
            raw_line(4, 5, market="USCA", category="Hats", date="3/15/2017 08:00")]
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(raw_dir / pipeline.RAW_FILENAME, index=False, encoding="latin1")
    return tmp_path


def test_bundle_gives_back_exactly_what_the_pipeline_computed(tmp_path):
    root = _project_with_tiny_raw(tmp_path)
    expected = pipeline.run_pipeline(root / "data" / "raw" / pipeline.RAW_FILENAME)
    pipeline.build_published(root)
    got = pipeline.load_published(root)
    pd.testing.assert_frame_equal(got.financial_rows, expected.financial_rows)            # ook de kolomtypes zijn gelijk
    pd.testing.assert_frame_equal(got.order_category_shipping, expected.order_category_shipping)
    assert got.stage_audit == expected.stage_audit
    assert got.grain_audit == expected.grain_audit
    assert got.quality_report == expected.quality_report
    assert got.source_manifest == expected.source_manifest


def test_bundle_contains_no_personal_columns(tmp_path):
    root = _project_with_tiny_raw(tmp_path)
    pipeline.build_published(root)
    for csv in (root / "data" / "published").glob("*.csv"):
        header = csv.read_text(encoding="utf-8").splitlines()[0].split(",")
        assert not [c for c in header if any(f in c.lower() for f in FORBIDDEN)], csv.name


def test_a_changed_bundle_file_is_refused(tmp_path):
    root = _project_with_tiny_raw(tmp_path)
    pipeline.build_published(root)
    table = next((root / "data" / "published").glob("dataco_financial_lines_*.csv"))
    table.write_bytes(table.read_bytes() + b"1,2,3\n")
    with pytest.raises(ValueError, match="SHA-256"):
        pipeline.load_published(root)


def test_an_existing_bundle_version_is_never_overwritten(tmp_path):
    root = _project_with_tiny_raw(tmp_path)
    pipeline.build_published(root)
    with pytest.raises(FileExistsError):
        pipeline.build_published(root)


def test_no_bundle_means_none(tmp_path):
    assert pipeline.load_published(tmp_path) is None
    assert pipeline.published_meta_path(tmp_path) is None


@pytest.mark.skipif(not pipeline.published_meta_path(ROOT), reason="no bundle under data/published/")
def test_the_shipped_bundle_has_only_analysis_columns():
    meta = json.loads(pipeline.published_meta_path(ROOT).read_text(encoding="utf-8"))
    allowed = set(pipeline.ANALYSIS_COLUMNS) | {"order_date", "is_late", "delivery_eligible", "delivery_status"}
    for name, info in meta["tables"].items():
        assert set(info["columns"]) <= allowed, name
        assert not [c for c in info["columns"] if any(f in c.lower() for f in FORBIDDEN)], name


@pytest.mark.skipif(not (RAW.is_file() and pipeline.published_meta_path(ROOT)), reason="needs the raw CSV and the bundle")
def test_the_shipped_bundle_matches_the_raw_data():
    expected = pipeline.run_pipeline(RAW)
    got = pipeline.load_published(ROOT)
    pd.testing.assert_frame_equal(got.financial_rows, expected.financial_rows)
    pd.testing.assert_frame_equal(got.order_category_shipping, expected.order_category_shipping)
    assert got.source_manifest["source_sha256"] == expected.source_manifest["source_sha256"]
