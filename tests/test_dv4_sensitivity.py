"""Gevoeligheid van DV4 voor de drempel van 30 orders (D-010, logboekrij 23).

Dezelfde prioriteitsregel met een andere minimumdrempel: de top 5 verandert niet, het aantal Prioriteit-segmenten wel (de mediaan van de omzet
schuift mee). Deze tests werken op de publicatiebundel (data/published/), dus ook zonder de ruwe CSV.
"""
from pathlib import Path

import pytest

import pipeline
from analysis.kpis import delivery_kpis, financial_kpis, priority_table

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(pipeline.published_meta_path(ROOT) is None, reason="geen publicatiebundel onder data/published/")

KEYS = ["Market", "Category Name"]
THRESHOLDS = (30, 50, 100, 300)


@pytest.fixture(scope="module")
def priorities():
    result = pipeline.load_published(ROOT)
    fin_kpi = financial_kpis(result.financial_rows, KEYS)
    del_kpi = delivery_kpis(result.order_category_shipping, KEYS)
    out = {}
    for threshold in THRESHOLDS:
        table, _ = priority_table(fin_kpi, del_kpi, min_orders=threshold)
        out[threshold] = list(table[table["priority"] == "Prioriteit"][KEYS].itertuples(index=False, name=None))
    return out


def test_the_top_5_is_the_same_for_every_threshold(priorities):
    top5 = priorities[30][:5]
    assert len(top5) == 5
    for threshold in THRESHOLDS:
        assert priorities[threshold][:5] == top5, threshold


def test_the_number_of_priority_segments_per_threshold(priorities):
    assert {t: len(priorities[t]) for t in THRESHOLDS} == {30: 18, 50: 17, 100: 14, 300: 9}


def test_a_higher_threshold_never_adds_a_priority_segment(priorities):
    base = set(priorities[30])
    for threshold in THRESHOLDS[1:]:
        assert set(priorities[threshold]) <= base, threshold
