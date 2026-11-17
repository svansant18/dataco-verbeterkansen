"""Gevoeligheid van DV4 voor de drempel van 30 orders (D-010, logboekrij 23).

Dezelfde prioriteitsregel met een andere minimumdrempel: de top 5 verandert niet, het aantal Prioriteit-segmenten wel (de mediaan van de omzet
schuift mee). Er is een kern van 9 segmenten die bij elke drempel Prioriteit zijn, en een top 20 is veel minder stabiel dan een top 5.
Deze tests werken op de publicatiebundel (data/published/), dus ook zonder de ruwe CSV.
"""
from pathlib import Path

import pytest

import pipeline
from analysis.kpis import RISK_CLASSES, delivery_kpis, financial_kpis, priority_table

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(pipeline.published_meta_path(ROOT) is None, reason="geen publicatiebundel onder data/published/")

KEYS = ["Market", "Category Name"]
THRESHOLDS = (30, 50, 100, 300)
CORE = [("LATAM", "Camping & Hiking"), ("Pacific Asia", "Cleats"), ("LATAM", "Indoor/Outdoor Games"), ("Europe", "Water Sports"),
        ("Pacific Asia", "Cardio Equipment"), ("USCA", "Cleats"), ("Pacific Asia", "Water Sports"), ("USCA", "Water Sports"), ("USCA", "Men's Footwear")]


@pytest.fixture(scope="module")
def lists():
    """Per drempel: de Prioriteit-segmenten en de ranglijst zoals de app ze toont (enkel risico-klassen met voldoende data; klasse, dan omzet)."""
    result = pipeline.load_published(ROOT)
    fin_kpi = financial_kpis(result.financial_rows, KEYS)
    del_kpi = delivery_kpis(result.order_category_shipping, KEYS)
    out = {}
    for threshold in THRESHOLDS:
        table, _ = priority_table(fin_kpi, del_kpi, min_orders=threshold)
        risk = table[table["enough_data"] & table["priority"].isin(RISK_CLASSES)]
        out[threshold] = {
            "priority": list(table[table["priority"] == "Prioriteit"][KEYS].itertuples(index=False, name=None)),
            "ranking": list(risk[KEYS].itertuples(index=False, name=None)),
        }
    return out


def test_the_top_5_is_the_same_for_every_threshold(lists):
    top5 = lists[30]["priority"][:5]
    assert len(top5) == 5
    for threshold in THRESHOLDS:
        assert lists[threshold]["priority"][:5] == top5, threshold


def test_the_number_of_priority_segments_per_threshold(lists):
    assert {t: len(lists[t]["priority"]) for t in THRESHOLDS} == {30: 18, 50: 17, 100: 14, 300: 9}


def test_a_higher_threshold_never_adds_a_priority_segment(lists):
    base = set(lists[30]["priority"])
    for threshold in THRESHOLDS[1:]:
        assert set(lists[threshold]["priority"]) <= base, threshold


def test_nine_segments_are_priority_at_every_threshold(lists):
    """De kern: precies deze 9 (de 9 grootste naar omzet) zijn bij elke drempel Prioriteit."""
    in_every_threshold = set.intersection(*[set(lists[t]["priority"]) for t in THRESHOLDS])
    assert in_every_threshold == set(CORE)
    assert lists[30]["priority"][:9] == CORE


def test_a_top_20_is_much_less_stable_than_a_top_5(lists):
    """Overlap van de top N met de top N bij drempel 30 (drempel 50, 100, 300). Een top 20 bevat bij 30 maar 18 Prioriteit en 2 Optimaliseren."""
    expected = {5: (5, 5, 5), 10: (10, 10, 9), 15: (15, 14, 9), 20: (19, 16, 13)}
    for n, overlaps in expected.items():
        base = set(lists[30]["ranking"][:n])
        got = tuple(len(base & set(lists[t]["ranking"][:n])) for t in THRESHOLDS[1:])
        assert got == overlaps, (n, got)
