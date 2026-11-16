"""Sub-app DV1: omzet en winst per markt en productcategorie.

Alle berekeningen staan in `pipeline.py`; dit bestand toont enkel. Geen zijbalk (CLAUDE.md, afspraak 8).
Kleuren volgen het dataviz-palet: één blauwe tint voor omvang, blauw <-> rood met grijs midden voor de
marge ten opzichte van het totaal.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dv1_omzet_winst import pipeline as pl  # noqa: E402

BLAUW = "#2a78d6"  # categorisch/sequentieel blauw (slot 1)
ROOD = "#e34948"  # categorisch rood (slot 8), laag einde van de marge-schaal
GRIJS_MIDDEN = "#f0efec"  # neutraal midden van de divergerende schaal
RASTER = "rgba(128,128,128,0.25)"  # recessief raster, werkt in licht en donker


# --------------------------------------------------------------------------- opmaak


def fmt_getal(n: float) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,.0f}".replace(",", ".")


def fmt_mln(x: float) -> str:
    """9348369 -> '9,35 mln'."""
    return f"{x / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " mln"


def fmt_pct(x: float) -> str:
    """0.1211 -> '12,1%'."""
    return f"{x * 100:.1f}".replace(".", ",") + "%"


# --------------------------------------------------------------------------- grafieken


def staafdiagram(tabel: pd.DataFrame, kolom_naam: str, meting: str, titel: str, horizontaal: bool = False) -> go.Figure:
    """Gerangschikte staven in één kleur; elke waarde heeft een direct label."""
    tabel = tabel.sort_values(meting, ascending=False)
    teksten = [fmt_pct(v) if meting == "marge" else fmt_mln(v) for v in tabel[meting]]
    hover = [
        f"<b>{naam}</b><br>Omzet: {fmt_mln(o)}<br>Winst: {fmt_mln(w)}<br>Marge: {fmt_pct(m)}<br>Orderlijnen: {fmt_getal(n)}"
        for naam, o, w, m, n in zip(tabel[kolom_naam], tabel["omzet"], tabel["winst"], tabel["marge"], tabel["orderlijnen"])
    ]
    staaf = dict(
        marker=dict(color=BLAUW, cornerradius=4),
        text=teksten,
        textposition="outside",
        cliponaxis=False,
        hovertext=hover,
        hoverinfo="text",
    )
    if horizontaal:
        fig = go.Figure(go.Bar(x=tabel[meting], y=tabel[kolom_naam], orientation="h", **staaf))
        fig.update_yaxes(autorange="reversed", title=None)
        fig.update_xaxes(showgrid=True, gridcolor=RASTER, title=None, tickformat=".0%" if meting == "marge" else None)
        hoogte = 24 * len(tabel) + 80
    else:
        fig = go.Figure(go.Bar(x=tabel[kolom_naam], y=tabel[meting], **staaf))
        fig.update_xaxes(title=None)
        fig.update_yaxes(showgrid=True, gridcolor=RASTER, title=None, tickformat=".0%" if meting == "marge" else None)
        hoogte = 340
    fig.update_layout(
        title=dict(text=titel, x=0, font=dict(size=15)),
        bargap=0.55,
        showlegend=False,  # één reeks: de titel benoemt ze
        margin=dict(l=10, r=60 if horizontaal else 10, t=50, b=10),
        height=hoogte,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def marge_heatmap(combi: pd.DataFrame, per_categorie: pd.DataFrame, per_markt: pd.DataFrame, totaal_marge: float) -> go.Figure:
    """Marge per categorie (rijen) en markt (kolommen), kleur t.o.v. de totale marge."""
    markten = list(per_markt["markt"])  # grootste omzet eerst
    categorieen = list(per_categorie["categorie"])
    ruimte = combi.set_index(["categorie", "markt"])

    def cel(cat: str, markt: str, kolom: str):
        return ruimte[kolom].get((cat, markt))

    z, tekst, hover = [], [], []
    for cat in categorieen:
        z_rij, t_rij, h_rij = [], [], []
        for markt in markten:
            marge = cel(cat, markt, "marge")
            if marge is None:
                z_rij.append(None)
                t_rij.append("")
                h_rij.append("")
                continue
            lijnen = int(cel(cat, markt, "orderlijnen"))
            weinig = lijnen < pl.MIN_LIJNEN
            z_rij.append(marge)
            t_rij.append(fmt_pct(marge) + ("*" if weinig else ""))
            h_rij.append(
                f"<b>{cat}</b> · {markt}<br>Marge: {fmt_pct(marge)}<br>"
                f"Omzet: {fmt_mln(cel(cat, markt, 'omzet'))}<br>Winst: {fmt_mln(cel(cat, markt, 'winst'))}<br>"
                f"Orderlijnen: {fmt_getal(lijnen)}" + (" (weinig data)" if weinig else "")
            )
        z.append(z_rij)
        tekst.append(t_rij)
        hover.append(h_rij)

    afwijking = max(abs(v - totaal_marge) for rij in z for v in rij if v is not None)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=markten,
            y=categorieen,
            text=tekst,
            texttemplate="%{text}",
            hovertext=hover,
            hoverinfo="text",
            hoverongaps=False,
            zmid=totaal_marge,
            zmin=totaal_marge - afwijking,
            zmax=totaal_marge + afwijking,
            colorscale=[[0, ROOD], [0.5, GRIJS_MIDDEN], [1, BLAUW]],
            xgap=2,
            ygap=2,
            colorbar=dict(title="Marge", tickformat=".0%", thickness=12),
        )
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(side="top", title=None)
    fig.update_layout(
        height=24 * len(categorieen) + 120,
        margin=dict(l=10, r=10, t=60, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# --------------------------------------------------------------------------- pagina's


@st.cache_resource(show_spinner="DV1 rekent...")
def draai_dv1() -> pl.DV1Resultaat:
    return pl.run_dv1()


def toon_kpis(totaal: dict) -> None:
    a, b, c, d = st.columns(4)
    a.metric("Omzet (na korting)", fmt_mln(totaal["omzet"]))
    b.metric("Winst", fmt_mln(totaal["winst"]))
    c.metric("Marge (winst / omzet)", fmt_pct(totaal["marge"]))
    d.metric("Orderlijnen", fmt_getal(totaal["orderlijnen"]), help=f"{fmt_getal(totaal['orders'])} unieke orders")


def toon_trechter(stappen: list[pl.StapInfo]) -> None:
    st.subheader("Trechter: van orderlijnen naar combinaties")
    tabel = pd.DataFrame(
        {
            "stap": [s.naam for s in stappen],
            "rijen in": [s.rijen_in for s in stappen],
            "rijen uit": [s.rijen_uit for s in stappen],
        }
    )
    st.caption("Rijen na elke stap. Stap 3 telt combinaties van markt en categorie, geen orderlijnen meer.")
    fig = go.Figure(go.Bar(x=tabel["rijen uit"], y=tabel["stap"], orientation="h", marker=dict(color=BLAUW, cornerradius=4),
                           text=[fmt_getal(n) for n in tabel["rijen uit"]], textposition="outside", cliponaxis=False,
                           hoverinfo="skip"))
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(visible=False)
    fig.update_layout(height=180, bargap=0.5, margin=dict(l=10, r=60, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")


def tab_markt(res: pl.DV1Resultaat) -> None:
    st.caption("Omzet, winst en marge per markt, elk in een eigen grafiek (één maat per grafiek).")
    links, midden, rechts = st.columns(3)
    with links:
        st.plotly_chart(staafdiagram(res.per_markt, "markt", "omzet", "Omzet per markt"), width="stretch")
    with midden:
        st.plotly_chart(staafdiagram(res.per_markt, "markt", "winst", "Winst per markt"), width="stretch")
    with rechts:
        st.plotly_chart(staafdiagram(res.per_markt, "markt", "marge", "Marge per markt"), width="stretch")
    spreiding = res.per_markt["marge"].max() - res.per_markt["marge"].min()
    st.info(
        f"De marge ligt per markt tussen {fmt_pct(res.per_markt['marge'].min())} en {fmt_pct(res.per_markt['marge'].max())} "
        f"(verschil {spreiding * 100:.1f} procentpunt): de markten verschillen vooral in omvang, veel minder in marge."
    )


def tab_categorie(res: pl.DV1Resultaat) -> None:
    meting = st.radio("Rangschik de categorieën op", ["omzet", "winst", "marge"], horizontal=True)
    titel = {"omzet": "Omzet per categorie", "winst": "Winst per categorie", "marge": "Marge per categorie"}[meting]
    st.plotly_chart(staafdiagram(res.per_categorie, "categorie", meting, titel, horizontaal=True), width="stretch")


def tab_heatmap(res: pl.DV1Resultaat) -> None:
    st.caption(
        f"Kleur toont de marge ten opzichte van het totaal ({fmt_pct(res.totaal['marge'])}): blauw is hoger, rood lager, "
        "grijs ongeveer gelijk. Rijen staan op omzet (grootste bovenaan), kolommen ook. "
        f"Een * betekent minder dan {pl.MIN_LIJNEN} orderlijnen: lees die marge voorzichtig. "
        "Lege cellen: die combinatie komt niet voor in de data."
    )
    st.plotly_chart(
        marge_heatmap(res.per_combinatie, res.per_categorie, res.per_markt, res.totaal["marge"]), width="stretch"
    )


def tab_tabel(res: pl.DV1Resultaat) -> None:
    niveau = st.radio("Detail", ["markt x categorie", "markt", "categorie"], horizontal=True)
    tabel = {"markt x categorie": res.per_combinatie, "markt": res.per_markt, "categorie": res.per_categorie}[niveau]
    st.dataframe(
        tabel,
        hide_index=True,
        width="stretch",
        column_config={
            "omzet": st.column_config.NumberColumn("omzet", format="%.0f"),
            "winst": st.column_config.NumberColumn("winst", format="%.0f"),
            "marge": st.column_config.NumberColumn("marge", format="percent"),
            "weinig_data": st.column_config.CheckboxColumn(f"< {pl.MIN_LIJNEN} lijnen"),
        },
    )
    if niveau == "categorie":
        st.caption("Een order kan meerdere categorieën bevatten, daarom is de som van `orders` hier groter dan het aantal unieke orders.")


def tab_stappen(res: pl.DV1Resultaat) -> None:
    for stap in res.stappen:
        with st.expander(f"{stap.naam}: {fmt_getal(stap.rijen_in)} → {fmt_getal(stap.rijen_uit)} rijen"):
            st.write(f"**Waarom:** {stap.reden}")
            st.write("**Voorbeeld na deze stap (eerste 5 rijen):**")
            st.dataframe(stap.voorbeeld, hide_index=True)


def main() -> None:
    st.title("DV1: omzet en winst per markt en categorie")
    st.write(
        "Omzet is **na korting** (`Order Item Total`), marge is **som winst / som omzet**. "
        "Geannuleerde en fraude-orders zijn uitgesloten. Zie `beslissingslogboek.md`."
    )
    try:
        res = draai_dv1()
    except FileNotFoundError as fout:
        st.error(str(fout))
        return
    toon_kpis(res.totaal)
    toon_trechter(res.stappen)
    markt, categorie, heatmap, tabel, stappen = st.tabs(["Per markt", "Per categorie", "Marge-heatmap", "Tabel", "Stappen"])
    with markt:
        tab_markt(res)
    with categorie:
        tab_categorie(res)
    with heatmap:
        tab_heatmap(res)
    with tabel:
        tab_tabel(res)
    with stappen:
        tab_stappen(res)


if __name__ == "__main__":
    st.set_page_config(page_title="DV1 Omzet en winst", layout="wide")
    main()
