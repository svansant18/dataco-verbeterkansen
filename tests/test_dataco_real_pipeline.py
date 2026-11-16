"""Checks on the REAL DataCo CSV (skipped on machines without the private file).

Technical evidence only: the business meaning of these checks still needs student review.
"""
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
    # Persoonsgegevens komen niet in de resultaten: de kolommen worden niet ingelezen (zie ook test_analysis_columns_contain_no_personal_data).
    assert not any(w in c for c in real.financial_rows.columns for w in ("Customer", "Email", "Password", "Street"))


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
    manual = real.financial_rows.groupby("Order Id")["is_late"].first()   # onafhankelijke route: per order de eerste rij van de analysebasis
    assert int(manual.sum()) == d["late_orders"]
