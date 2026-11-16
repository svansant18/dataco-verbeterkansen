"""Sub-app: pijplijn van de DataCo-dataset, stap voor stap inspecteerbaar.

Alle logica staat in `pipeline.py`; dit bestand toont enkel. Geen zijbalk (CLAUDE.md, afspraak 8).
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline_dataco import pipeline as pl  # noqa: E402


def fmt(n: int) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,}".replace(",", ".")


@st.cache_resource(show_spinner="Pijplijn draait (96 MB CSV inlezen)...")
def draai_pijplijn() -> pl.PijplijnResultaat:
    return pl.run_pipeline()


def toon_trechter(stappen: list[pl.StapInfo]) -> None:
    """Rijen- en kolommentrechter: in één oogopslag waar data verdwijnt."""
    st.subheader("Trechter: waar verdwijnt data?")
    tabel = pd.DataFrame(
        {
            "stap": [s.naam for s in stappen],
            "rijen in": [s.rijen_in for s in stappen],
            "rijen uit": [s.rijen_uit for s in stappen],
            "rijen weggevallen": [s.rijen_weggevallen for s in stappen],
            "kolommen in": [s.kolommen_in for s in stappen],
            "kolommen uit": [s.kolommen_uit for s in stappen],
        }
    )
    links, rechts = st.columns(2)
    with links:
        st.caption("Rijen na elke stap")
        st.bar_chart(tabel.set_index("stap")["rijen uit"])
    with rechts:
        st.caption("Kolommen na elke stap")
        st.bar_chart(tabel.set_index("stap")["kolommen uit"])
    st.dataframe(tabel, hide_index=True, width="stretch")
    totaal_weg = int(tabel["rijen weggevallen"].sum())
    st.caption(f"In totaal vallen {fmt(totaal_weg)} van {fmt(stappen[0].rijen_in)} rijen weg.")


def toon_wijzigingen(w: pl.Wijzigingen) -> None:
    """Toon wat er veranderde, enkel de onderdelen waar iets gebeurde."""
    if w.is_leeg():
        st.write("Geen wijzigingen aan kolommen of waarden.")
        return
    if w.rijen_voor != w.rijen_na:
        st.write(f"**Rijen:** {fmt(w.rijen_voor)} → {fmt(w.rijen_na)}")
    if w.kolommen_verwijderd:
        st.write("**Kolommen verwijderd:** " + ", ".join(f"`{c}`" for c in w.kolommen_verwijderd))
    if w.kolommen_toegevoegd:
        st.write("**Kolommen toegevoegd:** " + ", ".join(f"`{c}`" for c in w.kolommen_toegevoegd))
    if w.hernoemd:
        st.write("**Kolommen hernoemd:** " + ", ".join(f"`{o}` → `{n}`" for o, n in w.hernoemd.items()))
    if w.dtype_gewijzigd:
        st.write("**Datatype aangepast:**")
        st.dataframe(
            pd.DataFrame(
                [{"kolom": k, "voor": v[0], "na": v[1]} for k, v in w.dtype_gewijzigd.items()]
            ),
            hide_index=True,
        )
    if w.waarden_gewijzigd:
        st.write("**Tekstwaarden gewijzigd (aantal cellen):**")
        st.dataframe(
            pd.DataFrame([{"kolom": k, "aantal": n} for k, n in w.waarden_gewijzigd.items()]),
            hide_index=True,
        )
    if w.lege_waarden:
        st.write("**Aantal lege waarden veranderd:**")
        st.dataframe(
            pd.DataFrame([{"kolom": k, "voor": v[0], "na": v[1]} for k, v in w.lege_waarden.items()]),
            hide_index=True,
        )


def tab_stappen(res: pl.PijplijnResultaat) -> None:
    st.caption("Elke stap in een eigen uitklapbaar blok: rijen erin en eruit, de reden, wat er veranderde en een voorbeeld.")
    for stap in res.stappen:
        titel = f"{stap.naam}: {fmt(stap.rijen_in)} → {fmt(stap.rijen_uit)} rijen, {stap.kolommen_in} → {stap.kolommen_uit} kolommen"
        with st.expander(titel):
            st.write(f"**Waarom:** {stap.reden}")
            if stap.weggevallen_detail is not None:
                st.write("**Welke rijen vallen weg?**")
                st.dataframe(stap.weggevallen_detail, hide_index=True)
            toon_wijzigingen(stap.wijzigingen)
            st.write("**Voorbeeld na deze stap (eerste 5 rijen):**")
            st.dataframe(stap.voorbeeld, hide_index=True)


def tab_ruw_vs_verwerkt(res: pl.PijplijnResultaat) -> None:
    t = res.totaal
    st.caption(
        "Vergelijking van de ruwe CSV (`data/raw/`, ongewijzigd) met de eindtabel van de pijplijn. "
        "Dit is wat je moet weten voordat je een deelvraag beantwoordt."
    )
    a, b, c, d = st.columns(4)
    a.metric("Rijen ruw", fmt(t.rijen_voor))
    b.metric("Rijen verwerkt", fmt(t.rijen_na), delta=t.rijen_na - t.rijen_voor)
    c.metric("Kolommen ruw", res.ruw.shape[1])
    d.metric("Kolommen verwerkt", res.schoon.shape[1], delta=res.schoon.shape[1] - res.ruw.shape[1])

    st.subheader("Wat gebeurde er met elke kolom?")
    status = st.radio(
        "Toon kolommen met status",
        ["alle", "verwijderd", "type aangepast", "hernoemd", "behouden"],
        horizontal=True,
    )
    overzicht = res.overzicht if status == "alle" else res.overzicht[res.overzicht["status"] == status]
    st.dataframe(overzicht, hide_index=True, width="stretch")

    st.subheader("Voorbeelden van gewijzigde tekstwaarden")
    if t.waarden_gewijzigd:
        kolom = st.selectbox("Kolom", list(t.waarden_gewijzigd))
        oud = next((o for o, n in t.hernoemd.items() if n == kolom), kolom)
        st.caption(f"{fmt(t.waarden_gewijzigd[kolom])} cellen gewijzigd in `{kolom}`. Unieke voorbeelden (spaties zijn onzichtbaar):")
        voorbeeld = pl.voorbeelden_gewijzigd(res.ruw, res.schoon, oud, kolom)
        voorbeeld = voorbeeld.map(lambda x: f"'{x}'")
        st.dataframe(voorbeeld, hide_index=True)
    else:
        st.write("Geen tekstwaarden gewijzigd.")

    st.subheader("Verwerkte data opslaan")
    st.caption("Schrijft naar `data/processed/dataco_clean.csv`. De ruwe bestanden blijven onaangeroerd.")
    if st.button("Sla verwerkte data op als CSV"):
        pad = pl.save_processed(res.schoon)
        st.success(f"Opgeslagen: {pad}")


def tab_profiel(res: pl.PijplijnResultaat) -> None:
    keuze = st.radio("Dataprofiel van", ["verwerkte data", "ruwe data"], horizontal=True)
    profiel = res.profiel_schoon if keuze == "verwerkte data" else res.profiel_ruw
    st.caption("Per kolom: datatype, aantal ingevulde en lege waarden, unieke waarden, en min/max voor getallen en datums.")
    st.dataframe(profiel, hide_index=True, width="stretch")


def main() -> None:
    st.title("Pijplijn DataCo: van ruwe naar schone data")
    st.write(
        "Elke stap hieronder is een aparte functie in `pipeline.py`. Hier zie je wat erin en eruit gaat, "
        "waarom, en wat er veranderd is ten opzichte van de ruwe data."
    )
    res = draai_pijplijn()
    toon_trechter(res.stappen)
    stappen, vergelijking, profiel = st.tabs(["Stappen", "Ruw vs verwerkt", "Dataprofiel"])
    with stappen:
        tab_stappen(res)
    with vergelijking:
        tab_ruw_vs_verwerkt(res)
    with profiel:
        tab_profiel(res)


if __name__ == "__main__":
    st.set_page_config(page_title="Pijplijn DataCo", layout="wide")
    main()
