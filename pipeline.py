"""DataCo standalone Python pipeline (not an app).

Usage:
    python pipeline.py --input data/raw/DataCoSupplyChainDataset.csv \
        --report docs/data_audit_profile.json

The starter performs a privacy-safe SCHEMA PROFILE ONLY. Approved DataCo
cleaning, transformations, KPI calculations and row-drop accounting must be
added AFTER student approval of source/KPI definitions, with pure functions and independent tests.

This module does not import or execute Streamlit. No CSV is provided with the
starter package. The raw data are never written to the report file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import pandas as pd


@dataclass(frozen=True)
class StageCounts:
    """Audit a *row-grain* stage with mutually exclusive rejection reasons."""

    name: str
    rows_in: int
    rows_out: int
    primary_exclusion_reasons: Mapping[str, int]

    @property
    def rows_excluded(self) -> int:
        return self.rows_in - self.rows_out


def validate_stage_counts(stage: StageCounts) -> bool:
    """Conservation check for row-preserving transformations, no groupbys."""
    if stage.rows_in < 0 or stage.rows_out < 0 or stage.rows_out > stage.rows_in:
        raise ValueError("Invalid input/output row counts")
    if any(value < 0 for value in stage.primary_exclusion_reasons.values()):
        raise ValueError("Negative exclusion reason count")
    if sum(stage.primary_exclusion_reasons.values()) != stage.rows_excluded:
        raise ValueError("Rows excluded do not match exclusive reason counts")
    return True


def profile_input(df: pd.DataFrame) -> dict[str, object]:
    """Read-only basic metadata, without row values or personally identifiable data."""
    return {"rows": len(df), "columns": len(df.columns), "column_names": list(df.columns)}


def profile_schema(df: pd.DataFrame) -> dict[str, object]:
    """Pure schema profile; no business cleaning or private record values."""
    return {
        "status": "SCHEMA_ONLY_NOT_BUSINESS_VALIDATED",
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "fields": [
            {
                "name": str(col),
                "dtype": str(df.iloc[:, idx].dtype),
                "null_count": int(df.iloc[:, idx].isna().sum()),
            }
            for idx, col in enumerate(df.columns)
        ],
        "duplicate_header_count": int(df.columns.duplicated().sum()),
        "approved_data_rules": False,
        "remarks": "No rows excluded; no KPI calculated. Business decisions remain pending.",
    }


def read_source(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    """Explicit I/O boundary; throws on nonexistent/invalid source files."""
    if not path.is_file():
        raise FileNotFoundError(f"Source CSV not found: {path}")
    return pd.read_csv(path, encoding=encoding, low_memory=False)


def file_sha256(path: Path) -> str:
    """Compute a source/output fingerprint without changing the file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def persist_processed_dataset(
    df: pd.DataFrame,
    *,
    source_path: Path,
    output_name: str,
    transformation_steps: list[str],
    decision_ids: list[str],
    project_root: Path = Path("."),
    encoding: str = "utf-8-sig",
) -> tuple[Path, Path]:
    """Persist a NEW derived CSV and its manifest under data/processed/ only.

    The original data/raw CSV is opened exclusively for hashing, never for writing.
    Caller supplies approved transformations and their logged decision identifiers.
    This does not execute or approve any business transformation itself.
    """
    root = Path(project_root).resolve()
    raw_dir = (root / "data" / "raw").resolve()
    processed_dir = (root / "data" / "processed").resolve()
    source = Path(source_path)
    source = (root / source).resolve() if not source.is_absolute() else source.resolve()
    if not source.is_relative_to(raw_dir) or not source.is_file() or source.suffix.lower() != ".csv":
        raise ValueError("Source must be an existing CSV under data/raw/ only")
    name_path = Path(output_name)
    if name_path.name != output_name or output_name in (".", "..") or name_path.suffix.lower() != ".csv":
        raise ValueError("output_name must be a plain .csv filename without directories")
    if not transformation_steps or not all(isinstance(s, str) and s.strip() for s in transformation_steps):
        raise ValueError("Supply nonempty transformation_steps for provenance")
    if not decision_ids or not all(isinstance(s, str) and s.strip() for s in decision_ids):
        raise ValueError("Supply nonempty approved decision_ids for provenance")

    if processed_dir == raw_dir or processed_dir.is_relative_to(raw_dir) or raw_dir.is_relative_to(processed_dir):
        raise ValueError("data/processed/ must be a separate directory from data/raw/")

    target = processed_dir / output_name
    metadata_path = target.with_suffix(".provenance.json")
    if target.exists() or metadata_path.exists():
        raise FileExistsError("Processed output already exists; use a new versioned filename")

    raw_hash_before = file_sha256(source)
    input_rows = len(pd.read_csv(source, usecols=[0], encoding=encoding))  # record count without retaining raw data
    processed_dir.mkdir(parents=True, exist_ok=True)
    temporary_csv: Path | None = None
    temporary_meta: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".csv.tmp", dir=processed_dir, delete=False, newline="") as output:
            temporary_csv = Path(output.name)
            df.to_csv(output, index=False)
        output_hash = file_sha256(temporary_csv)
        raw_hash_after = file_sha256(source)
        if raw_hash_before != raw_hash_after:
            raise RuntimeError("Raw source changed during processing; refusing to publish derived output")
        metadata = {
            "source_file": str(source.relative_to(raw_dir)),
            "source_sha256": raw_hash_before,
            "processed_file": output_name,
            "processed_sha256": output_hash,
            "input_rows": int(input_rows),
            "output_rows": int(len(df)),
            "transformation_steps": transformation_steps,
            "decision_ids": decision_ids,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "STORED_LOCALLY_NOT_PUBLICATION_APPROVED",
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json.tmp", dir=processed_dir, delete=False) as output:
            temporary_meta = Path(output.name)
            json.dump(metadata, output, indent=2, ensure_ascii=False)
            output.write("\n")
        # Both final paths were checked before writing, so ordinary repeated
        # calls refuse existing versions. Temporary files are removed on failure.
        if target.exists() or metadata_path.exists():
            raise FileExistsError("Processed output exists; cannot overwrite")
        os.replace(temporary_csv, target)
        temporary_csv = None
        os.replace(temporary_meta, metadata_path)
        temporary_meta = None
    finally:
        for item in (temporary_csv, temporary_meta):
            if item is not None:
                item.unlink(missing_ok=True)
    return target, metadata_path


def write_profile(profile: dict[str, object], path: Path, project_root: Path = Path(".")) -> Path:
    """Write a schema report outside data/raw/ and data/processed/.

    This blocks accidental overwrites of raw CSVs (including via symlinks) and
    prevents mixing audit reports with versioned processed datasets.
    """
    root = Path(project_root).resolve()
    target = Path(path)
    target = (root / target).resolve() if not target.is_absolute() else target.resolve()
    raw_dir = (root / "data" / "raw").resolve()
    processed_dir = (root / "data" / "processed").resolve()
    if target.is_relative_to(raw_dir) or target.is_relative_to(processed_dir):
        raise ValueError("Audit reports cannot be written under data/raw/ or data/processed/")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only DataCo schema profile. Not a Streamlit app.")
    parser.add_argument("--input", type=Path, required=True, help="Path to local CSV under data/raw/")
    parser.add_argument("--report", type=Path, default=Path("docs/data_audit_profile.json"))
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding, e.g. utf-8-sig or latin1")
    args = parser.parse_args(argv)
    raw_hash_before = file_sha256(args.input)
    df = read_source(args.input, args.encoding)
    report_path = write_profile(profile_schema(df), args.report)
    raw_hash_after = file_sha256(args.input)
    if raw_hash_before != raw_hash_after:
        raise RuntimeError("Raw source changed during schema profiling")
    print(f"Schema profile saved to {report_path}: {len(df)} source rows; ZERO transformations applied.")
    print("Next step: audit fields and approve G0/G1 before DataCo cleaning and KPI logic.")
    return 0


def audit_order_grain(df: pd.DataFrame) -> dict[str, object]:
    """Return only counts/metadata, never raw customer/order identifiers.

    This is an exploratory grain audit, not a decision to aggregate KPI fields.
    """
    if "Order Id" not in df.columns:
        return {"status": "MISSING_ORDER_ID", "order_id_column_present": False}

    keys = df["Order Id"].astype("string").str.strip()
    valid_mask = keys.notna() & keys.ne("")
    valid_keys = keys[valid_mask]
    order_line_counts = valid_keys.value_counts(dropna=True)
    summary: dict[str, object] = {
        "status": "AUDIT_ONLY_NOT_BUSINESS_VALIDATED",
        "order_id_column_present": True,
        "source_rows": int(len(df)),
        "rows_with_missing_order_id": int((~valid_mask).sum()),
        "unique_order_ids": int(valid_keys.nunique()),
        "orders_with_multiple_rows": int((order_line_counts > 1).sum()),
        "max_rows_per_order": int(order_line_counts.max()) if not order_line_counts.empty else 0,
    }
    if "Order Item Id" in df.columns:
        item_ids = df["Order Item Id"].astype("string").str.strip()
        item_present = item_ids.notna() & item_ids.ne("")
        summary["missing_order_item_id"] = int((~item_present).sum())
        summary["duplicate_order_item_id_rows"] = int(item_ids[item_present].duplicated().sum())
    if "Category Name" in df.columns:
        temp = pd.DataFrame({"key": valid_keys, "category": df.loc[valid_mask, "Category Name"].astype("string")})
        cat_counts = temp.groupby("key", dropna=False)["category"].nunique(dropna=True)
        summary["orders_spanning_multiple_categories"] = int((cat_counts > 1).sum())
    if "Delivery Status" in df.columns:
        temp = pd.DataFrame({"key": valid_keys, "status": df.loc[valid_mask, "Delivery Status"].astype("string")})
        counts = temp.groupby("key", dropna=False)["status"].nunique(dropna=True)
        summary["orders_with_conflicting_non_null_delivery_statuses"] = int((counts > 1).sum())
        summary["rows_with_missing_delivery_status"] = int(df["Delivery Status"].isna().sum())
    return summary


# ---------------------------------------------------------------------------
# DataCo analysis pipeline (V9). Pure functions, no Streamlit.
# Decisions: D-006..D-010 in beslissingslogboek.md (student answers 2026-11-16).
# ---------------------------------------------------------------------------

SOURCE_ENCODING = "latin1"
RAW_FILENAME = "DataCoSupplyChainDataset.csv"  # data/raw bevat ook de omschrijving en de access logs: die zijn buiten scope
DATE_FORMAT = "%m/%d/%Y %H:%M"
DECISION_IDS = ["D-006", "D-007", "D-008", "D-010"]

# PII columns (Customer Email, Customer Password, names, addresses ...) are never
# read: only the columns below are loaded from the raw CSV.
ANALYSIS_COLUMNS = (
    "Order Id", "Order Item Id", "Market", "Category Name", "order date (DateOrders)",
    "Sales", "Order Item Total", "Order Profit Per Order",
    "Order Item Discount", "Order Item Discount Rate",
    "Delivery Status", "Late_delivery_risk", "Order Status",
)
REQUIRED_NOT_NULL = tuple(c for c in ANALYSIS_COLUMNS if c != "Late_delivery_risk")

LATE_STATUS = "Late delivery"
CANCELED_SHIPPING_STATUS = "Shipping canceled"
KNOWN_DELIVERY_STATUSES = frozenset({LATE_STATUS, CANCELED_SHIPPING_STATUS, "Advance shipping", "Shipping on time"})
# D-007: orders that never realised revenue are out of scope for revenue/profit.
EXCLUDED_ORDER_STATUSES = {"CANCELED": "order_status_canceled", "SUSPECTED_FRAUD": "order_status_suspected_fraud"}


@dataclass(frozen=True)
class PipelineResult:
    financial_rows: pd.DataFrame          # order-line grain, in-scope (D-007)
    order_category_shipping: pd.DataFrame  # unique (order, market, category), ALL orders incl. ineligible
    stage_audit: tuple[StageCounts, ...]   # row-grain stages only (real drops)
    grain_audit: dict[str, object]
    quality_report: dict[str, object]
    source_manifest: dict[str, object]


def read_analysis_source(path: Path, encoding: str = SOURCE_ENCODING) -> pd.DataFrame:
    """Read only the analysis columns (no personal data ever enters memory)."""
    if not Path(path).is_file():
        raise FileNotFoundError(f"Source CSV not found: {path}")
    return pd.read_csv(path, encoding=encoding, usecols=list(ANALYSIS_COLUMNS), low_memory=False)


def _exclusive_reasons(conditions: list[tuple[str, pd.Series]], index: pd.Index) -> pd.Series:
    """Assign each row at most ONE reason: the first matching condition wins."""
    reason = pd.Series("", index=index, dtype="object")
    for name, mask in conditions:
        reason = reason.mask((reason == "") & mask, name)
    return reason


def _stage(name: str, df: pd.DataFrame, reason: pd.Series) -> tuple[pd.DataFrame, StageCounts]:
    keep = reason == ""
    counts = {str(k): int(v) for k, v in reason[~keep].value_counts().items()}
    stage = StageCounts(name, len(df), int(keep.sum()), counts)
    validate_stage_counts(stage)
    return df.loc[keep].copy(), stage


def step_validate(df: pd.DataFrame) -> tuple[pd.DataFrame, StageCounts]:
    """Stage 2: keys, required values, parseable order date, unique order line."""
    missing_cols = [c for c in REQUIRED_NOT_NULL if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required source columns: {missing_cols}")
    order_date = pd.to_datetime(df["order date (DateOrders)"], format=DATE_FORMAT, errors="coerce")
    reason = _exclusive_reasons(
        [
            ("missing_order_or_line_id", df["Order Id"].isna() | df["Order Item Id"].isna()),
            ("missing_required_value", df[list(REQUIRED_NOT_NULL)].isna().any(axis=1)),
            ("invalid_order_date", order_date.isna()),
            ("duplicate_order_item_id", df.duplicated("Order Item Id", keep="first")),
        ],
        df.index,
    )
    out, stage = _stage("Validatie", df.assign(order_date=order_date), reason)
    return out, stage


def step_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, StageCounts]:
    """Stage 3: retype/trim only. Rows are preserved; unknown statuses stop the run (no guessing)."""
    out = df.copy()
    for col in ("Market", "Category Name", "Delivery Status", "Order Status"):
        out[col] = out[col].astype("string").str.strip()
    unknown = sorted(set(out["Delivery Status"].unique()) - KNOWN_DELIVERY_STATUSES)
    if unknown:
        raise ValueError(f"Unmapped Delivery Status values (needs an approved decision): {unknown}")
    for col in ("Sales", "Order Item Total", "Order Profit Per Order", "Order Item Discount", "Order Item Discount Rate"):
        out[col] = pd.to_numeric(out[col], errors="raise")
    out["Order Id"] = out["Order Id"].astype("int64")
    out["Order Item Id"] = out["Order Item Id"].astype("int64")
    out["is_late"] = out["Delivery Status"].eq(LATE_STATUS).to_numpy(dtype=bool)
    out["delivery_eligible"] = out["Delivery Status"].ne(CANCELED_SHIPPING_STATUS).to_numpy(dtype=bool)
    stage = StageCounts("Opschonen", len(df), len(out), {})
    validate_stage_counts(stage)
    return out, stage


def step_scope(df: pd.DataFrame) -> tuple[pd.DataFrame, StageCounts]:
    """Stage 4 (D-007): leave out orders that never realised revenue."""
    reason = _exclusive_reasons(
        [(label, df["Order Status"].eq(status)) for status, label in EXCLUDED_ORDER_STATUSES.items()],
        df.index,
    )
    return _stage("Analysebasis (omzet/winst)", df, reason)


def build_order_category_shipping(clean: pd.DataFrame) -> pd.DataFrame:
    """Order x category grain (D-008). Raises when one order carries conflicting statuses."""
    conflict = clean.groupby("Order Id")["Delivery Status"].nunique()
    if (conflict > 1).any():
        raise ValueError(f"{int((conflict > 1).sum())} orders with conflicting Delivery Status; no silent first()")
    market_conflict = clean.groupby("Order Id")["Market"].nunique()
    if (market_conflict > 1).any():
        raise ValueError("Orders spanning multiple markets; define a rule first")
    grouped = clean.groupby(["Order Id", "Market", "Category Name"], observed=True).agg(
        order_date=("order_date", "min"),
        delivery_status=("Delivery Status", "first"),
        is_late=("is_late", "first"),
        delivery_eligible=("delivery_eligible", "first"),
    )
    return grouped.reset_index()


def audit_grain(clean: pd.DataFrame, financial: pd.DataFrame, ocs: pd.DataFrame) -> dict[str, object]:
    cat_per_order = clean.groupby("Order Id")["Category Name"].nunique()
    status_per_order = clean.groupby("Order Id")["Delivery Status"].nunique()
    profit_values_per_order = clean.groupby("Order Id")["Order Profit Per Order"].nunique()
    date_per_order = clean.groupby("Order Id")["order_date"].nunique()
    orders_all = int(clean["Order Id"].nunique())
    orders_fin = int(financial["Order Id"].nunique())
    order_level = ocs.drop_duplicates("Order Id")
    scope_orders = set(financial["Order Id"])
    eligible_orders = set(order_level.loc[order_level["delivery_eligible"], "Order Id"])
    return {
        "order_lines": int(len(clean)),
        "unique_orders": orders_all,
        "unique_orders_in_financial_scope": orders_fin,
        "unique_orders_delivery_eligible": len(eligible_orders),
        "orders_with_multiple_lines": int((clean.groupby("Order Id").size() > 1).sum()),
        "orders_spanning_multiple_categories": int((cat_per_order > 1).sum()),
        "order_category_pairs": int(len(ocs)),
        "sum_of_category_orders_exceeds_unique_orders_by": int(len(ocs) - orders_all),
        "orders_with_conflicting_delivery_status": int((status_per_order > 1).sum()),
        "orders_with_varying_profit_value_across_lines": int((profit_values_per_order > 1).sum()),
        "profit_field_is_line_level_not_repeated_order_total": bool((profit_values_per_order > 1).any()),
        "orders_with_multiple_order_dates": int((date_per_order > 1).sum()),
        "financial_scope_equals_delivery_eligible_orders": scope_orders == eligible_orders,
        "market_category_combinations_financial": int(financial.groupby(["Market", "Category Name"]).ngroups),
    }


def build_quality_report(raw: pd.DataFrame, financial: pd.DataFrame) -> dict[str, object]:
    cross = raw["Late_delivery_risk"].astype("Int64").eq(raw["Delivery Status"].eq(LATE_STATUS).astype("Int64"))
    raw_categories = raw["Category Name"].dropna().astype("string")
    trimmed = raw_categories.str.strip()
    return {
        "category_names_with_surrounding_whitespace": int((raw_categories.drop_duplicates() != raw_categories.drop_duplicates().str.strip()).sum()),
        "category_names_merged_by_trimming": int(raw_categories.nunique() - trimmed.nunique()),
        "late_delivery_risk_matches_delivery_status_rows": int(cross.sum()),
        "late_delivery_risk_mismatch_rows": int((~cross).sum()),
        "zero_or_negative_revenue_lines_in_scope": int((financial["Order Item Total"] <= 0).sum()),
        "negative_profit_lines_in_scope_kept": int((financial["Order Profit Per Order"] < 0).sum()),
        "discount_rate_min": float(financial["Order Item Discount Rate"].min()),
        "discount_rate_max": float(financial["Order Item Discount Rate"].max()),
        "discount_rate_unit": "fraction 0-1" if financial["Order Item Discount Rate"].max() <= 1 else "percentage 0-100 (mixed unit risk)",
        "order_period_start": str(financial["order_date"].min().date()),
        "order_period_end": str(financial["order_date"].max().date()),
        "pii_columns_loaded": 0,
    }


def run_pipeline(source: Path, encoding: str = SOURCE_ENCODING) -> PipelineResult:
    """Run the full, read-only pipeline on one raw CSV; raw hash is checked before and after."""
    source = Path(source)
    hash_before = file_sha256(source)
    raw = read_analysis_source(source, encoding)
    start = StageCounts("Bron ingelezen", len(raw), len(raw), {})
    validated, s_valid = step_validate(raw)
    cleaned, s_clean = step_clean(validated)
    financial, s_scope = step_scope(cleaned)
    ocs = build_order_category_shipping(cleaned)
    if file_sha256(source) != hash_before:
        raise RuntimeError("Raw source changed during the pipeline run")
    manifest = {
        "source_file": source.name,
        "source_sha256": hash_before,
        "raw_hash_unchanged_after_run": True,
        "source_rows": int(len(raw)),
        "encoding": encoding,
        "columns_loaded": list(ANALYSIS_COLUMNS),
        "decision_ids": DECISION_IDS,
    }
    return PipelineResult(
        financial_rows=financial.reset_index(drop=True),
        order_category_shipping=ocs,
        stage_audit=(start, s_valid, s_clean, s_scope),
        grain_audit=audit_grain(cleaned, financial, ocs),
        quality_report=build_quality_report(raw, financial),
        source_manifest=manifest,
    )


STAGE_MODES = {"Bron ingelezen": "transform", "Validatie": "filter", "Opschonen": "transform", "Analysebasis (omzet/winst)": "filter"}


def write_row_funnel(result: PipelineResult, processed_sha256: str, project_root: Path = Path(".")) -> Path:
    """Write the OBSERVED row funnel (from the real run) to reports/local/, never into data/."""
    root = Path(project_root).resolve()
    stages = [
        {"name": s.name, "mode": STAGE_MODES[s.name], "rows_in": s.rows_in, "rows_out": s.rows_out,
         "primary_exclusion_reasons": dict(s.primary_exclusion_reasons)}
        for s in result.stage_audit
    ]
    if stages[-1]["rows_out"] != len(result.financial_rows):
        raise ValueError("Funnel does not end at the analysis base")
    payload = {
        "source_sha256": result.source_manifest["source_sha256"], "processed_sha256": processed_sha256, "stages": stages,
        "grain_conversions_not_exclusions": {
            "order_lines": result.grain_audit["order_lines"], "unique_orders": result.grain_audit["unique_orders"],
            "order_category_pairs": result.grain_audit["order_category_pairs"],
        },
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return write_profile(payload, root / "reports" / "local" / "row_funnel.json", project_root=root)


def build_processed(project_root: Path = Path("."), version: str = "v1") -> list[tuple[Path, Path]]:
    """Persist the in-scope analysis tables as NEW versions under data/processed/ (never overwrites)."""
    root = Path(project_root).resolve()
    candidates = [root / "data" / "raw" / RAW_FILENAME]
    if not candidates[0].is_file():
        raise ValueError(f"Expected {RAW_FILENAME} under data/raw/, not found")
    result = run_pipeline(candidates[0])
    steps = [s.name for s in result.stage_audit] + ["Order x categorie-grain (unieke orders)"]
    out = []
    for name, frame in (("financial_lines", result.financial_rows), ("order_category_shipping", result.order_category_shipping)):
        out.append(persist_processed_dataset(
            frame, source_path=candidates[0], output_name=f"dataco_{name}_{version}.csv",
            transformation_steps=steps, decision_ids=DECISION_IDS, project_root=root, encoding=SOURCE_ENCODING,
        ))
    meta = json.loads(out[0][1].read_text(encoding="utf-8"))
    write_row_funnel(result, meta["processed_sha256"], root)
    return out


if __name__ == "__main__":
    raise SystemExit(main())
