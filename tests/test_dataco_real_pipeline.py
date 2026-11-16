"""Checks on the REAL DataCo CSV (skipped on machines without the private file).

Technical evidence only: the business meaning of these checks still needs student review.
"""
import json
from pathlib import Path

import pytest

import pipeline
from analysis.kpis import delivery_kpis, financial_kpis

ROOT = Path(__file__).resolve().parents[1]
RAW = [p for p in [ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"] if p.is_file()]
pytestmark = pytest.mark.skipif(len(RAW) != 1, reason="no raw CSV under data/raw/")


@pytest.fixture(scope="module")
def real():
    return pipeline.run_pipeline(RAW[0])


def test_real_funnel_adds_up_and_raw_unchanged(real):
    s = real.stage_audit
    assert s[0].rows_in == 180519
    assert s[-1].rows_out == s[0].rows_in - sum(x.rows_excluded for x in s)
    assert real.source_manifest["raw_hash_unchanged_after_run"]
    assert real.source_manifest["source_sha256"] == pipeline.file_sha256(RAW[0])
    assert real.quality_report["pii_columns_loaded"] == 0
    assert not any("Email" in c or "Password" in c for c in real.financial_rows.columns)


def test_profit_is_line_level_in_real_data(real):
    g = real.grain_audit
    assert g["profit_field_is_line_level_not_repeated_order_total"] is True
    assert g["orders_with_conflicting_delivery_status"] == 0
    assert g["financial_scope_equals_delivery_eligible_orders"] is True
    assert real.quality_report["discount_rate_unit"] == "fraction 0-1"


def test_real_totals_reconcile_between_grains(real):
    fin = financial_kpis(real.financial_rows).iloc[0]
    by_market = financial_kpis(real.financial_rows, ["Market"])
    assert by_market["revenue"].sum() == pytest.approx(fin["revenue"])
    assert by_market["profit"].sum() == pytest.approx(fin["profit"])
    d = delivery_kpis(real.order_category_shipping).iloc[0]
    assert d["eligible_orders"] == real.grain_audit["unique_orders_delivery_eligible"]
    assert d["orders_all"] == real.grain_audit["unique_orders"]
    manual = real.financial_rows.groupby("Order Id")["is_late"].first()   # independent path: processed frame, one row per order
    assert int(manual.sum()) == d["late_orders"]


def test_processed_files_match_their_provenance(real):
    manifests = sorted((ROOT / "data" / "processed").glob("dataco_financial_lines_*.provenance.json"))
    if not manifests:
        pytest.skip("no processed version built yet")
    meta = json.loads(manifests[-1].read_text(encoding="utf-8"))
    processed = ROOT / "data" / "processed" / meta["processed_file"]
    assert pipeline.file_sha256(processed) == meta["processed_sha256"]
    assert meta["source_sha256"] == real.source_manifest["source_sha256"]
    assert meta["output_rows"] == len(real.financial_rows)
    assert meta["input_rows"] == real.stage_audit[0].rows_in
