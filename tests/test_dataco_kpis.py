"""Tests for the DataCo pipeline steps and KPI logic (hand-made data + real-data checks when the CSV exists)."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pipeline
from analysis.evidence import KPI_REGISTER
from analysis.kpis import (Filters, MIN_ORDERS, apply_filters, delivery_kpis, discount_class, financial_kpis,
                           priority_table)

ROOT = Path(__file__).resolve().parents[1]
RAW = [p for p in [ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"] if p.is_file()]


def raw_line(order, item, market="Europe", category="Cleats", status="Late delivery", order_status="COMPLETE",
             total=100.0, profit=10.0, rate=0.1, date="1/31/2018 22:56"):
    return {
        "Order Id": order, "Order Item Id": item, "Market": market, "Category Name": category, "order date (DateOrders)": date,
        "Sales": total / (1 - rate), "Order Item Total": total, "Order Profit Per Order": profit,
        "Order Item Discount": total / (1 - rate) - total, "Order Item Discount Rate": rate,
        "Delivery Status": status, "Late_delivery_risk": int(status == "Late delivery"), "Order Status": order_status,
    }


def run_steps(rows):
    df = pd.DataFrame(rows)
    valid, s1 = pipeline.step_validate(df)
    clean, s2 = pipeline.step_clean(valid)
    scoped, s3 = pipeline.step_scope(clean)
    return df, clean, scoped, (s1, s2, s3)


def test_stage_conservation():
    rows = [raw_line(1, 1), raw_line(2, 2, order_status="CANCELED", status="Shipping canceled"),
            raw_line(3, 3, order_status="SUSPECTED_FRAUD", status="Shipping canceled"),
            raw_line(4, 4, date="not a date"), raw_line(5, 5), raw_line(5, 5)]
    df = pd.DataFrame(rows)
    valid, s1 = pipeline.step_validate(df)
    assert s1.primary_exclusion_reasons == {"invalid_order_date": 1, "duplicate_order_item_id": 1}
    clean, s2 = pipeline.step_clean(valid)
    scoped, s3 = pipeline.step_scope(clean)
    for s in (s1, s2, s3):
        assert pipeline.validate_stage_counts(s)
        assert sum(s.primary_exclusion_reasons.values()) == s.rows_excluded
    assert s3.primary_exclusion_reasons == {"order_status_canceled": 1, "order_status_suspected_fraud": 1}
    assert len(scoped) == len(df) - s1.rows_excluded - s3.rows_excluded


def test_margin_is_weighted_not_mean_of_margins():
    fin = pd.DataFrame([raw_line(1, 1, total=100, profit=50), raw_line(2, 2, total=900, profit=90)])
    fin["Market"], fin["Category Name"] = "Europe", "Cleats"
    out = financial_kpis(fin, ["Market"]).iloc[0]
    assert out["margin_pct"] == pytest.approx(14.0)          # (50+90)/(100+900)
    assert out["margin_pct"] != pytest.approx(30.0)          # mean of 50% and 10%


def test_zero_revenue_margin_is_nan():
    fin = pd.DataFrame([raw_line(1, 1, total=0.0, profit=0.0)])
    assert np.isnan(financial_kpis(fin, ["Market"]).iloc[0]["margin_pct"])
    assert np.isnan(financial_kpis(fin).iloc[0]["margin_pct"])


def test_order_with_two_categories_counts_once_per_group():
    rows = [raw_line(1, 1, category="Cleats"), raw_line(1, 2, category="Cleats"), raw_line(1, 3, category="Shoes"),
            raw_line(2, 4, category="Cleats", status="Shipping on time")]
    _, clean, _, _ = run_steps(rows)
    ocs = pipeline.build_order_category_shipping(clean)
    by_cat = delivery_kpis(ocs, ["Market", "Category Name"]).set_index("Category Name")
    assert by_cat.loc["Cleats", "eligible_orders"] == 2 and by_cat.loc["Cleats", "late_orders"] == 1
    assert by_cat.loc["Shoes", "eligible_orders"] == 1
    total = delivery_kpis(ocs).iloc[0]
    assert total["eligible_orders"] == 2                      # unique orders, NOT 3 (sum of categories)
    assert by_cat["eligible_orders"].sum() == 3
    fin = financial_kpis(clean, ["Market"]).iloc[0]
    assert fin["lines"] == 4 and fin["orders"] == 2           # lines != orders


def test_conflicting_status_raises():
    rows = [raw_line(1, 1, status="Late delivery"), raw_line(1, 2, status="Shipping on time")]
    _, clean, _, _ = run_steps(rows)
    with pytest.raises(ValueError, match="conflicting"):
        pipeline.build_order_category_shipping(clean)


def test_unknown_delivery_status_stops_the_run():
    with pytest.raises(ValueError, match="Unmapped Delivery Status"):
        run_steps([raw_line(1, 1, status="Lost in space")])


def test_canceled_shipping_out_of_denominator():
    rows = [raw_line(1, 1, status="Late delivery"), raw_line(2, 2, status="Shipping on time"),
            raw_line(3, 3, status="Shipping canceled", order_status="CANCELED")]
    _, clean, _, _ = run_steps(rows)
    ocs = pipeline.build_order_category_shipping(clean)
    out = delivery_kpis(ocs).iloc[0]
    assert (out["orders_all"], out["eligible_orders"], out["late_orders"], out["excluded_orders"]) == (3, 2, 1, 1)
    assert out["late_pct"] == pytest.approx(50.0)


def test_discount_class_boundaries():
    rate = pd.Series([0.0, 0.01, 0.05, 0.0501, 0.10, 0.11, 0.20, 0.21, 0.25])
    labels = discount_class(rate).astype(str).tolist()
    assert labels == ["0%", ">0-5%", ">0-5%", ">5-10%", ">5-10%", ">10-20%", ">10-20%", ">20%", ">20%"]


def test_filter_consistency():
    rows = [raw_line(1, 1, market="Europe", date="1/1/2017 10:00"), raw_line(2, 2, market="LATAM", date="6/1/2017 10:00"),
            raw_line(3, 3, market="Europe", date="1/1/2018 10:00")]
    _, clean, _, _ = run_steps(rows)
    ocs = pipeline.build_order_category_shipping(clean)
    f = Filters(market="Europe", date_from=pd.Timestamp("2017-01-01"), date_to=pd.Timestamp("2017-12-31"))
    fin_f, ocs_f = apply_filters(clean, f), apply_filters(ocs, f)
    assert fin_f["Order Id"].nunique() == ocs_f["Order Id"].nunique() == 1   # same scope for KPI and detail
    assert financial_kpis(fin_f).iloc[0]["orders"] == delivery_kpis(ocs_f).iloc[0]["orders_all"]
    last_day = Filters(date_from=pd.Timestamp("2018-01-01"), date_to=pd.Timestamp("2018-01-01"))
    assert len(apply_filters(clean, last_day)) == 1                          # whole end day included


def _segment(market, category, revenue, profit, eligible, late):
    return (
        {"Market": market, "Category Name": category, "revenue": revenue, "profit": profit, "margin_pct": 100 * profit / revenue, "lines": eligible, "orders": eligible},
        {"Market": market, "Category Name": category, "eligible_orders": eligible, "late_orders": late, "late_pct": 100 * late / eligible},
    )


def test_priority_min_orders_and_tiebreak():
    segs = [
        _segment("A", "x", 1000, 50, 100, 80),   # big, low margin, very late  -> Prioriteit
        _segment("B", "x", 1000, 50, 100, 80),   # identical -> tie-break on market name
        _segment("C", "x", 5000, 500, 10, 9),    # < MIN_ORDERS -> Onvoldoende data (never 'Sterk')
        _segment("D", "x", 2000, 400, 100, 20),  # healthy margin, few late -> Sterk
    ]
    fin = pd.DataFrame([s[0] for s in segs])
    dlv = pd.DataFrame([s[1] for s in segs])
    table, refs = priority_table(fin, dlv)
    assert refs["min_orders"] == MIN_ORDERS == 30
    by = table.set_index("Market")
    assert by.loc["C", "priority"] == "Onvoldoende data"
    assert by.loc["D", "priority"] == "Sterk"
    assert list(table["Market"][:2]) == ["A", "B"]           # same class + revenue -> alphabetical
    assert by.loc["A", "priority"] == by.loc["B", "priority"] == "Prioriteit"
    assert table.iloc[-1]["priority"] == "Onvoldoende data"   # always last


def test_priority_boundary_exactly_min_orders_qualifies():
    seg_ok = _segment("A", "x", 1000, 50, MIN_ORDERS, 20)
    seg_low = _segment("B", "x", 1000, 50, MIN_ORDERS - 1, 20)
    table, _ = priority_table(pd.DataFrame([seg_ok[0], seg_low[0]]), pd.DataFrame([seg_ok[1], seg_low[1]]))
    by = table.set_index("Market")
    assert by.loc["A", "enough_data"] and not by.loc["B", "enough_data"]


def test_register_references_real_tests():
    missing = []
    for d in KPI_REGISTER.values():
        for t in d["test_ids"]:
            path, name = t.split("::")
            text = (ROOT / path).read_text(encoding="utf-8")
            if f"def {name}(" not in text:
                missing.append(t)
    assert not missing, missing



def test_the_correlation_has_its_own_register_entry_with_its_own_tests():
    """De correlatie is geen verhouding van twee sommen: ze heeft een eigen KPI met eigen controles, los van de marge per kortingsklasse."""
    corr, classes = KPI_REGISTER["K-CORR"], KPI_REGISTER["K-DISC"]
    assert "Spearman" in corr["formula"] and corr["numerator"] == "-" and corr["denominator"] == "-"
    assert len(corr["test_ids"]) == 2 and all("spearman" in t.lower() for t in corr["test_ids"])
    assert "correlatie" not in classes["formula"].lower() and classes["numerator"] == "som winst" and classes["denominator"] == "som omzet"
