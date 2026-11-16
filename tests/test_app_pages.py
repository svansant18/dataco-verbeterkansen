"""De app echt openen (Streamlit AppTest): alle pagina's draaien, ook met een filter. Overgeslagen zonder de ruwe CSV."""
import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "DataCoSupplyChainDataset.csv"
pytestmark = pytest.mark.skipif(not RAW.is_file(), reason="no raw CSV under data/raw/")

PAGES = ["views/overview.py", "views/dv1.py", "views/dv2.py", "views/dv3.py", "views/dv4.py", "views/methode.py"]


def _open():
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=300).run()


def _first_chart_x(at):
    """De x-waarden van de eerste grafiek op de pagina (plotly bewaart de figuur als JSON)."""
    proto = at.get("plotly_chart")[0].proto
    spec = getattr(proto, "spec", None) or proto.figure.spec
    return json.loads(spec)["data"][0]["x"]


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


def test_market_filter_compares_categories_not_one_bar():
    at = _open()
    at.switch_page("views/dv1.py").run()
    assert set(_first_chart_x(at)) == {"Africa", "Europe", "LATAM", "Pacific Asia", "USCA"}   # zonder filter: per markt
    at.selectbox(key="global_market").select("Europe")
    at.run()
    at.switch_page("views/dv1.py").run()
    x = _first_chart_x(at)
    assert len(set(x)) > 1 and "Europe" not in x          # met een markt: categorieën, meer dan één staaf


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
