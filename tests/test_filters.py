"""Filters en DV4: een filter op markt of categorie zoomt in; de klassen en referenties veranderen niet (logboek 19)."""
from pathlib import Path

import pandas as pd
import pytest

import pipeline
from analysis.kpis import (Filters, apply_filters, available_options, comparison_dimension, delivery_kpis, financial_kpis,
                           nothing_to_compare, priority_table, prioritize_selection)
from test_dataco_kpis import raw_line, run_steps

ROOT = Path(__file__).resolve().parents[1]
RAW = [p for p in [ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"] if p.is_file()]
KEYS = ["Market", "Category Name"]


def _segment(rows, market, category, n_orders, total, profit, n_late):
    start = len(rows) + 1
    for i in range(n_orders):
        status = "Late delivery" if i < n_late else "Shipping on time"
        rows.append(raw_line(start + i, start + i, market=market, category=category, status=status, total=total, profit=profit))


def _small_company():
    """Vier segmenten, elk 4 orders. Uitgerekend: referentie marge 11,2%, vertraagd 50%, mediaan omzet 3.000."""
    rows = []
    _segment(rows, "Europe", "Cleats", 4, 1000, 50, 3)   # veel omzet, marge 5%, 75% laat  -> Prioriteit
    _segment(rows, "Europe", "Shoes", 4, 1000, 200, 0)   # marge 20%, nooit laat           -> Sterk
    _segment(rows, "LATAM", "Cleats", 4, 500, 10, 4)     # weinig omzet, marge 2%, 100% laat -> Optimaliseren
    _segment(rows, "LATAM", "Shoes", 4, 100, 30, 1)      # marge 30%, 25% laat             -> Sterk
    _, clean, scoped, _ = run_steps(rows)
    return scoped, pipeline.build_order_category_shipping(clean)


def _classes(table):
    return dict(zip(zip(table["Market"], table["Category Name"]), table["priority"]))


def test_zooming_in_on_a_category_keeps_the_class_of_every_segment():
    fin, ocs = _small_company()
    everything, refs_all, _, _ = prioritize_selection(fin, ocs, min_orders=2)
    zoomed, refs_zoom, _, _ = prioritize_selection(fin, ocs, category="Cleats", min_orders=2)
    assert len(everything) == 4 and len(zoomed) == 2
    assert set(zoomed["Category Name"]) == {"Cleats"}
    assert refs_zoom == refs_all                                   # dezelfde referenties
    for segment, klasse in _classes(zoomed).items():
        assert klasse == _classes(everything)[segment]
    assert _classes(everything)[("Europe", "Cleats")] == "Prioriteit"


def test_filtering_before_the_calculation_would_change_the_class_that_is_why_we_do_not():
    """Bewijst dat de fixture iets controleert: vroeg filteren geeft Europe/Cleats een andere klasse dan zonder filter."""
    fin, ocs = _small_company()
    everything, _, _, _ = prioritize_selection(fin, ocs, min_orders=2)
    f = Filters(category="Cleats")
    naive, _ = priority_table(financial_kpis(apply_filters(fin, f), KEYS), delivery_kpis(apply_filters(ocs, f), KEYS), min_orders=2)
    assert _classes(naive)[("Europe", "Cleats")] != _classes(everything)[("Europe", "Cleats")]


def test_zooming_in_on_a_market_keeps_references_and_classes():
    fin, ocs = _small_company()
    everything, refs_all, _, _ = prioritize_selection(fin, ocs, min_orders=2)
    zoomed, refs_zoom, _, _ = prioritize_selection(fin, ocs, market="LATAM", min_orders=2)
    assert set(zoomed["Market"]) == {"LATAM"} and len(zoomed) == 2
    assert refs_zoom == refs_all
    assert all(_classes(zoomed)[s] == _classes(everything)[s] for s in _classes(zoomed))


def _tiny_frame():
    return pd.DataFrame({
        "Market": ["Europe", "Europe", "LATAM"],
        "Category Name": ["Cleats", "Hats", "Cleats"],
        "order_date": pd.to_datetime(["2017-01-01", "2017-06-01", "2017-06-01"]),
    })


def test_options_depend_on_the_other_filter_and_on_the_period():
    """Afhankelijke filters: je kan alleen kiezen wat bestaat, dus nooit een lege combinatie."""
    fin = _tiny_frame()
    assert available_options(fin, Filters()) == (["Europe", "LATAM"], ["Cleats", "Hats"])
    assert available_options(fin, Filters(market="LATAM")) == (["Europe", "LATAM"], ["Cleats"])     # LATAM verkoopt geen Hats
    assert available_options(fin, Filters(category="Hats")) == (["Europe"], ["Cleats", "Hats"])     # Hats bestaat enkel in Europe
    in_january = Filters(date_to=pd.Timestamp("2017-02-01"))
    assert available_options(fin, in_january) == (["Europe"], ["Cleats"])                           # de periode telt mee


@pytest.mark.skipif(not RAW, reason="no raw CSV under data/raw/")
def test_real_data_no_offered_combination_is_empty():
    fin = pipeline.run_pipeline(RAW[0]).financial_rows
    markets, categories = available_options(fin, Filters())
    assert len(markets) == 5 and len(categories) == 50
    for market in markets:
        offered = available_options(fin, Filters(market=market))[1]
        assert offered, market
        assert all(not apply_filters(fin, Filters(market=market, category=c)).empty for c in offered), market
    for category in categories:
        offered = available_options(fin, Filters(category=category))[0]
        assert all(not apply_filters(fin, Filters(market=m, category=category)).empty for m in offered), category


def test_one_market_compares_categories_otherwise_markets():
    """Met één markt zou 'per markt' maar één staaf tonen: dan vergelijken we categorieën."""
    assert comparison_dimension(Filters()) == ("Market", "markt", "markten")
    assert comparison_dimension(Filters(category="Cleats")) == ("Market", "markt", "markten")
    assert comparison_dimension(Filters(market="Europe")) == ("Category Name", "categorie", "categorieën")
    assert comparison_dimension(Filters(market="Europe", category="Cleats"))[0] == "Category Name"


def test_nothing_to_compare_only_when_both_market_and_category_are_chosen():
    assert not nothing_to_compare(Filters())
    assert not nothing_to_compare(Filters(market="Europe"))
    assert not nothing_to_compare(Filters(category="Cleats"))
    assert nothing_to_compare(Filters(market="Europe", category="Cleats"))


@pytest.mark.skipif(not RAW, reason="no raw CSV under data/raw/")
def test_real_data_zooming_in_never_changes_a_class():
    result = pipeline.run_pipeline(RAW[0])
    fin, ocs = result.financial_rows, result.order_category_shipping
    everything, _, _, _ = prioritize_selection(fin, ocs)
    expected = _classes(everything)
    categories = sorted(fin["Category Name"].unique())
    choices = [dict(market=m) for m in sorted(fin["Market"].unique())] + [dict(category=c) for c in categories[::5]]
    for choice in choices:
        zoomed, _, _, _ = prioritize_selection(fin, ocs, **choice)
        assert not zoomed.empty, choice
        assert all(_classes(zoomed)[s] == expected[s] for s in _classes(zoomed)), choice
