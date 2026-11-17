"""De app echt openen (Streamlit AppTest): alle pagina's draaien, ook met een filter. Overgeslagen zonder de ruwe CSV."""
import json
from datetime import date
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


def _chart_types(at):
    """Het soort grafiek (bar, heatmap, ...) van elke plotly-grafiek op de pagina, van boven naar onder."""
    kinds = []
    for chart in at.get("plotly_chart"):
        proto = chart.proto
        spec = getattr(proto, "spec", None) or proto.figure.spec
        kinds.append(json.loads(spec)["data"][0]["type"])
    return kinds


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


def test_the_heatmap_stays_when_a_market_is_chosen():
    """De heatmap rechts op DV1 en DV2 blijft staan, ook met een marktfilter (logboek 21)."""
    at = _open()
    for market in (None, "Europe"):
        if market:
            at.selectbox(key="global_market").select(market)
            at.run()
        for page in ("views/dv1.py", "views/dv2.py"):
            at.switch_page(page).run()
            assert _chart_types(at)[:2] == ["bar", "heatmap"], (market, page)


def test_category_options_follow_the_chosen_market():
    """Afhankelijke filters: met een markt gekozen bieden de categorieën alleen wat in die markt voorkomt."""
    at = _open()
    every_category = list(at.selectbox(key="global_category").options)
    at.selectbox(key="global_market").select("Africa")
    at.run()
    offered = list(at.selectbox(key="global_category").options)
    assert offered[0] == "Alle categorieën" and 1 < len(offered) < len(every_category)


def test_market_options_follow_the_chosen_category():
    """De categorie CDs komt maar in twee markten voor."""
    at = _open()
    at.selectbox(key="global_category").select("CDs")
    at.run()
    assert list(at.selectbox(key="global_market").options) == ["Alle markten", "Europe", "Pacific Asia"]


def test_a_choice_that_becomes_impossible_falls_back_to_all():
    """CDs bestaat alleen in okt-dec 2017: in de eerste twee dagen van 2015 springt de categorie terug op 'Alle'."""
    at = _open()
    at.selectbox(key="global_category").select("CDs")
    at.run()
    at.date_input(key="global_period").set_value((date(2015, 1, 1), date(2015, 1, 2)))
    at.run()
    assert at.selectbox(key="global_category").value == "Alle categorieën"
    assert not at.exception


def test_the_app_works_without_the_raw_csv_and_shows_the_same_numbers(monkeypatch):
    """Online staat de ruwe CSV er niet. De app valt dan terug op de publicatiebundel en toont dezelfde KPI-kaarten."""
    def numbers():
        at = _open()
        found = {}
        for market in (None, "Europe"):
            if market:
                at.selectbox(key="global_market").select(market)
                at.run()
            for page in PAGES:
                at.switch_page(page).run()
                assert not at.exception, (market, page)
                found[(market, page)] = [(m.label, m.value) for m in at.metric]
        return found

    with_raw = numbers()
    monkeypatch.setenv("DATACO_BRON", "bundel")
    assert numbers() == with_raw


def test_the_source_is_credited_on_data_and_methode():
    """De dataset staat onder een licentie die bronvermelding eist (CC BY 4.0 volgens Mendeley): de naam, de DOI en de bewerking staan in de app."""
    at = _open()
    at.switch_page("views/methode.py").run()
    text = " ".join(str(c.value) for c in at.caption)
    assert "Constante" in text and "10.17632/8gx2fvg2k6" in text and "CC BY 4.0" in text and "Bewerkt" in text


def test_no_chart_needs_webgl():
    """WebGL is niet in elke browser beschikbaar (hardwareversnelling uit, virtuele machine, schoolcomputer): dan toont Plotly
    "WebGL not supported by your browser" in plaats van de grafiek. Geen enkele grafiek mag dus een WebGL-trace (scattergl) gebruiken."""
    at = _open()
    for page in PAGES:
        at.switch_page(page).run()
        assert not at.exception, page
        for chart in at.get("plotly_chart"):
            proto = chart.proto
            spec = json.loads(getattr(proto, "spec", None) or proto.figure.spec)
            kinds = {trace["type"] for trace in spec["data"]}
            assert not any(k.endswith("gl") for k in kinds), (page, kinds)


def test_dv3_shows_the_correlation_and_the_class_margin_as_separate_kpis():
    """In "Hoe is dit berekend?" op DV3 staat de marge per kortingsklasse (met teller en noemer) los van de correlatie (zonder teller en noemer)."""
    at = _open()
    at.switch_page("views/dv3.py").run()
    assert not at.exception
    text = "\n".join(str(m.value) for m in at.markdown)
    assert "`K-DISC`" in text and "`K-CORR`" in text
    corr_block = text.split("`K-CORR`", 1)[1].split("####", 1)[0]
    assert "teller: —" in corr_block and "noemer: —" in corr_block
    assert "test_spearman_with_ties_matches_hand_calculation" in corr_block
    disc_block = text.split("`K-DISC`", 1)[1].split("####", 1)[0]
    assert "teller: —" not in disc_block and "(som winst)" in disc_block and "(som omzet)" in disc_block


def test_the_dataset_is_not_called_real_in_the_status_line():
    """We kunnen niet bewijzen dat de dataset "echt" is (de leverstatus hangt niet samen met de orderstatus): de app noemt haar de gepubliceerde DataCo-dataset."""
    at = _open()
    text = " ".join(str(c.value) for c in at.caption)
    assert "gepubliceerde DataCo-dataset" in text and "echte DataCo-data" not in text


def test_overview_states_the_spread_of_late_orders_from_the_data():
    """De Overview toont de spreiding van het % te laat uit de data (per markt, of per categorie bij een marktfilter) en geen vaste conclusie."""
    at = _open()
    at.switch_page("views/overview.py").run()
    assert not at.exception
    text = " ".join(str(m.value) for m in at.markdown)
    assert "breed patroon" not in text and "geen uitschieter" not in text
    assert "per markt loopt dat van" in text and "procentpunt (zie DV2)" in text
    at.selectbox(key="global_market").select("Europe").run()
    at.switch_page("views/overview.py").run()
    text = " ".join(str(m.value) for m in at.markdown)
    assert "per categorie loopt dat van" in text
