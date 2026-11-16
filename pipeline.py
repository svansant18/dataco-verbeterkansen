"""DataCo-pijplijn: pure functies (geen Streamlit) die de ruwe CSV in stappen verwerkt.

Stappen: inlezen -> valideren -> opschonen -> analysebasis (omzet en winst) -> order x categorie.
Elke stap telt hoeveel rijen erin en eruit gaan en waarom (zie StageCounts).
De ruwe CSV wordt nooit aangepast en persoonsgegevens worden niet ingelezen (zie ANALYSIS_COLUMNS).
"""

from __future__ import annotations

import hashlib
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


def file_sha256(path: Path) -> str:
    """Compute a source/output fingerprint without changing the file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    """Geef elke rij hoogstens ÉÉN reden: de eerste voorwaarde die past wint.

    Zo tellen de redenen in de rijentrechter exact op tot het aantal weggevallen rijen.
    """
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
    """Stap 2: controleer de sleutels, de verplichte waarden, een leesbare orderdatum en unieke orderregels.

    Een rij die faalt valt weg met één reden (zie _exclusive_reasons).
    """
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
    """Stap 3: enkel types zetten en tekst trimmen. Er vallen geen rijen weg.

    Een onbekende leverstatus stopt de run: we gokken niet wat die betekent.
    """
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
    """Stap 4 (D-007): laat orders weg die nooit omzet opleverden (geannuleerd of vermoedelijke fraude)."""
    reason = _exclusive_reasons(
        [(label, df["Order Status"].eq(status)) for status, label in EXCLUDED_ORDER_STATUSES.items()],
        df.index,
    )
    return _stage("Analysebasis (omzet/winst)", df, reason)


def build_order_category_shipping(clean: pd.DataFrame) -> pd.DataFrame:
    """Grain 'order × categorie' (D-008): elke order telt één keer per categorie waarin hij zit.

    Geeft een fout als één order tegenstrijdige leverstatussen of meer dan één markt heeft:
    we kiezen niet stil de eerste.
    """
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
    """Draai de hele pijplijn op één ruwe CSV (alleen lezen). De hash van de bron wordt vóór en na gecontroleerd."""
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

