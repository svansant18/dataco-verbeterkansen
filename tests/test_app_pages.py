"""De app echt openen (Streamlit AppTest): alle pagina's draaien, ook met een filter. Overgeslagen zonder de ruwe CSV."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"
pytestmark = pytest.mark.skipif(not RAW.is_file(), reason="no raw CSV under data/raw/")

PAGES = ["views/overview.py", "views/dv1.py", "views/dv2.py", "views/dv3.py", "views/dv4.py", "views/methode.py"]
DV_PAGES = PAGES[1:5]


def _open():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=300).run()


def _chart_axis(at, axis):
    """De x- of y-waarden van de eerste grafiek op de pagina (plotly bewaart de figuur als JSON)."""
    proto = at.get("plotly_chart")[0].proto
    spec = getattr(proto, "spec", None) or proto.figure.spec
    return json.loads(spec)["data"][0][axis]


def _all_pages_run(at):
    for page in PAGES:
        at.switch_page(page).run()
        assert not at.exception, (page, [e.value for e in at.exception])


def test_all_pages_open_without_errors():
    _all_pages_run(_open())


def test_all_pages_open_with_a_market_filter_and_with_both_filters():
    at = _open()
    at.selectbox(key="global_market").select("Europe")
    at.run()
    _all_pages_run(at)
    at.selectbox(key="global_category").select("Cleats")   # nu markt én categorie: niets te vergelijken
    at.run()
    _all_pages_run(at)


def test_every_dv_page_has_both_evidence_expanders():
    at = _open()
    for page in DV_PAGES:
        at.switch_page(page).run()
        labels = " | ".join(e.label for e in at.expander)
        assert "Hoe is dit berekend?" in labels and "Onderliggende data" in labels, page


def test_market_filter_compares_categories_not_one_bar():
    at = _open()
    at.switch_page("views/dv1.py").run()
    assert set(_chart_axis(at, "x")) == {"Africa", "Europe", "LATAM", "Pacific Asia", "USCA"}   # zonder filter: per markt
    at.selectbox(key="global_market").select("Europe")
    at.run()
    at.switch_page("views/dv1.py").run()
    x = _chart_axis(at, "x")
    assert len(set(x)) > 1 and "Europe" not in x          # met een markt: categorieën, meer dan één staaf


def test_dv2_and_overview_also_compare_categories_with_a_market_filter():
    at = _open()
    at.selectbox(key="global_market").select("Europe")
    at.run()
    at.switch_page("views/dv2.py").run()
    x = _chart_axis(at, "x")
    assert len(set(x)) > 1 and "Europe" not in x
    at.switch_page("views/overview.py").run()
    y = _chart_axis(at, "y")                               # op Overview liggen de balken horizontaal
    assert len(set(y)) > 1 and "Europe" not in y


def test_top_list_says_so_when_a_selection_has_no_segment_with_a_risk():
    """Logboek 25. De categorie 'CDs' heeft twee segmenten met voldoende data en beide zijn 'Sterk'."""
    at = _open()
    at.selectbox(key="global_category").select("CDs")
    at.run()
    for page in ("views/overview.py", "views/dv4.py"):
        at.switch_page(page).run()
        assert any("Geen segment met een risico" in i.value for i in at.info), page


def test_dv4_reference_stays_fixed_when_filtering_on_a_category():
    """Wat de gebruiker ziet: de referentiekaart van DV4 blijft die van het hele bedrijf. (De klassen zelf test test_filters.py.)"""
    at = _open()
    at.switch_page("views/dv4.py").run()
    unfiltered = {m.label: m.value for m in at.metric}
    assert unfiltered["Segmenten met Prioriteit"] == "18"
    at.selectbox(key="global_category").select("Water Sports")
    at.run()
    at.switch_page("views/dv4.py").run()
    shown = {m.label: m.value for m in at.metric}
    assert shown["Referentie marge · vertraging"] == unfiltered["Referentie marge · vertraging"]   # vaste referentie
