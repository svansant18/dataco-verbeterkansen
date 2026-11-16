"""DV1-DV4 on the REAL data, recomputed independently from the raw CSV (own pandas code, no pipeline/analysis imports
for the expected values). Skipped when the private CSV is not on this machine. Business meaning still needs student review.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import pipeline
from analysis.kpis import MIN_ORDERS, delivery_kpis, financial_kpis, margin_by_discount_class, priority_table

ROOT = Path(__file__).resolve().parents[1]
RAW = [p for p in [ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"] if p.is_file()]
pytestmark = pytest.mark.skipif(len(RAW) != 1, reason="no raw CSV under data/raw/")

COLS = ["Order Id", "Market", "Category Name", "Order Item Total", "Order Profit Per Order", "Order Item Discount Rate", "Delivery Status", "Order Status"]


@pytest.fixture(scope="module")
def result():
    return pipeline.run_pipeline(RAW[0])


@pytest.fixture(scope="module")
def raw_scope():
    """Independent view: raw lines minus CANCELED / SUSPECTED_FRAUD orders."""
    df = pd.read_csv(RAW[0], encoding="latin1", usecols=COLS, low_memory=False)
    for col in ("Market", "Category Name", "Delivery Status", "Order Status"):
        df[col] = df[col].str.strip()   # the source has trailing spaces in some category names ('Baby ', 'Cameras ', ...)
    return df[~df["Order Status"].isin(["CANCELED", "SUSPECTED_FRAUD"])]


def test_dv1_market_totals_match_raw(result, raw_scope):
    expected = raw_scope.groupby("Market").agg(rev=("Order Item Total", "sum"), prof=("Order Profit Per Order", "sum"), lines=("Order Id", "size"), orders=("Order Id", "nunique"))
    got = financial_kpis(result.financial_rows, ["Market"])
    got.index = got["Market"].astype(str)          # align by label; avoids pandas string-dtype differences
    expected.index = expected.index.astype(str)
    expected = expected.reindex(got.index)
    assert not expected.isna().any().any()
    assert np.allclose(got["revenue"], expected["rev"], rtol=1e-9) and np.allclose(got["profit"], expected["prof"], rtol=1e-9)
    assert (got["lines"] == expected["lines"]).all() and (got["orders"] == expected["orders"]).all()
    assert np.allclose(got["margin_pct"], 100 * expected["prof"] / expected["rev"], rtol=1e-9)


def test_dv1_total_margin_is_weighted(result, raw_scope):
    tot = financial_kpis(result.financial_rows).iloc[0]
    assert tot["margin_pct"] == pytest.approx(100 * raw_scope["Order Profit Per Order"].sum() / raw_scope["Order Item Total"].sum())
    # Not asserted as 'very different': overall the weighted margin (12.03%) and the mean of line margins (12.06%) are
    # close on this data. The weighted definition is still the correct one (and differs more in small segments).
    line_mean = (100 * raw_scope["Order Profit Per Order"] / raw_scope["Order Item Total"]).mean()
    assert tot["margin_pct"] != pytest.approx(line_mean, abs=1e-6)


def test_dv2_market_and_category_late_rates_match_raw(result, raw_scope):
    orders = raw_scope.drop_duplicates("Order Id")
    exp_m = orders.groupby("Market").agg(n=("Order Id", "size"), late=("Delivery Status", lambda s: int((s == "Late delivery").sum())))
    got_m = delivery_kpis(result.order_category_shipping, ["Market"]).set_index("Market")
    assert (got_m["eligible_orders"] == exp_m["n"]).all() and (got_m["late_orders"] == exp_m["late"]).all()
    pairs = raw_scope.drop_duplicates(["Order Id", "Category Name"])
    exp_c = pairs.groupby(["Market", "Category Name"]).agg(n=("Order Id", "size"), late=("Delivery Status", lambda s: int((s == "Late delivery").sum())))
    got_c = delivery_kpis(result.order_category_shipping, ["Market", "Category Name"])
    got_c.index = pd.MultiIndex.from_arrays([got_c["Market"].astype(str), got_c["Category Name"].astype(str)])
    exp_c.index = pd.MultiIndex.from_arrays([exp_c.index.get_level_values(0).astype(str), exp_c.index.get_level_values(1).astype(str)])
    joined = got_c.join(exp_c, how="inner")
    assert len(joined) == len(exp_c)
    assert (joined["eligible_orders"] == joined["n"]).all() and (joined["late_orders"] == joined["late"]).all()


def test_dv2_category_counts_exceed_unique_orders(result):
    total = delivery_kpis(result.order_category_shipping).iloc[0]["eligible_orders"]
    by_cat = delivery_kpis(result.order_category_shipping, ["Category Name"])["eligible_orders"].sum()
    assert by_cat > total   # multi-category orders: categories must never be summed into an order total


def test_dv3_class_margins_match_raw(result, raw_scope):
    bins, labels = [-0.0001, 0.0, 0.05, 0.10, 0.20, 1.0], ["0%", ">0-5%", ">5-10%", ">10-20%", ">20%"]
    cls = pd.cut(raw_scope["Order Item Discount Rate"], bins=bins, labels=labels, include_lowest=True)
    exp = raw_scope.groupby(cls, observed=True).apply(lambda g: 100 * g["Order Profit Per Order"].sum() / g["Order Item Total"].sum(), include_groups=False)
    got = margin_by_discount_class(result.financial_rows).set_index("discount_class")["margin_pct"]
    for label in exp.index:
        assert got.loc[label] == pytest.approx(exp.loc[label])
    assert margin_by_discount_class(result.financial_rows)["lines"].sum() == len(raw_scope)


def test_dv3_spearman_matches_independent_rank_correlation(result, raw_scope):
    from analysis.kpis import discount_margin_correlation
    margin = raw_scope["Order Profit Per Order"] / raw_scope["Order Item Total"]
    exp = raw_scope["Order Item Discount Rate"].rank().corr(margin.rank())
    assert discount_margin_correlation(result.financial_rows)["spearman"] == pytest.approx(exp, abs=1e-9)


def test_dv4_priorities_follow_the_rules_and_trace_to_dv1_dv2(result):
    fin = financial_kpis(result.financial_rows, ["Market", "Category Name"])
    dlv = delivery_kpis(result.order_category_shipping, ["Market", "Category Name"])
    table, refs = priority_table(fin, dlv)
    assert refs["min_orders"] == MIN_ORDERS
    # nothing below the minimum may be ranked as anything except 'Onvoldoende data'
    assert (table.loc[table["eligible_orders"] < MIN_ORDERS, "priority"] == "Onvoldoende data").all()
    prio = table[table["priority"] == "Prioriteit"]
    assert not prio.empty
    assert (prio["eligible_orders"] >= MIN_ORDERS).all()
    assert (prio["margin_pct"] < refs["ref_margin_pct"]).all() and (prio["late_pct"] > refs["ref_late_pct"]).all()
    assert (prio["revenue"] >= refs["median_revenue_qualifying"]).all()
    # every DV4 number is literally the DV1/DV2 number for that segment
    merged = table.merge(fin, on=["Market", "Category Name"], suffixes=("", "_dv1")).merge(dlv, on=["Market", "Category Name"], suffixes=("", "_dv2"))
    assert np.allclose(merged["revenue"], merged["revenue_dv1"]) and np.allclose(merged["late_pct"], merged["late_pct_dv2"])
    # references are the weighted totals, not averages of segment values
    assert refs["ref_margin_pct"] == pytest.approx(100 * fin["profit"].sum() / fin["revenue"].sum())
    assert refs["ref_late_pct"] == pytest.approx(100 * dlv["late_orders"].sum() / dlv["eligible_orders"].sum())
    # deterministic: identical input -> identical ranking
    again, _ = priority_table(fin.sample(frac=1, random_state=1), dlv.sample(frac=1, random_state=2))
    assert list(again["Market"] + "|" + again["Category Name"]) == list(table["Market"] + "|" + table["Category Name"])
