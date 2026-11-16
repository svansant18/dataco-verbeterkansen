"""Sub-app DV4: verbeterprioriteiten, welke combinaties van markt en categorie verdienen als eerste onderzoek?

Alle berekeningen staan in `pipeline.py`; dit bestand toont enkel. Geen zijbalk (CLAUDE.md, afspraak 8):
de drempel staat op de hoofdpagina. De app claimt geen oorzaak en geen besparing.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dv4_verbeterprioriteiten import pipeline as pl  # noqa: E402

BLAUW = "#2a78d6"  # reeks 1: één probleem
ORANJE = "#eb6834"  # reeks 2: nadruk op 'dubbel probleem'
GRIJS = "#898781"  # gedempt: op koers en groepen zonder rang
RASTER = "rgba(128,128,128,0.25)"  # recessief raster, werkt in licht en donker


# --------------------------------------------------------------------------- opmaak


def fmt_mln(x: float) -> str:
    """9348369 -> '9,35 mln'."""
    return f"{x / 1e6:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " mln"


def fmt_pp(x: float) -> str:
    """-0.0123 -> '-1,2 pp' (procentpunt)."""
    return f"{x * 100:+.1f}".replace(".", ",") + " pp"


fmt_getal, fmt_pct = pl.fmt_getal, pl.fmt_pct


# --------------------------------------------------------------------------- grafieken


def hover_tekst(r) -> str:
    rang = f"Rang {int(r.rang)}" if pd.notna(r.rang) else "Geen rang (te weinig orderlijnen)"
    return (
        f"<b>{r.categorie}</b> · {r.markt}<br>{rang}<br>"
        f"Marge: {fmt_pct(r.marge)} ({fmt_pp(r.marge_verschil)} t.o.v. totaal)<br>"
        f"Vertraagd: {fmt_pct(r.pct_vertraagd)} ({fmt_pp(r.vertraging_verschil)} t.o.v. totaal)<br>"
        f"Omzet: {fmt_mln(r.omzet)} ({fmt_pct(r.omzetaandeel)} van totaal)<br>"
        f"Orderlijnen: {fmt_getal(r.orderlijnen)}<br>{r.groep}"
    )


def prioriteitenmatrix(tabel: pd.DataFrame, totaal: dict) -> go.Figure:
    """Marge (x) tegen percentage vertraagd (y), bolgrootte = omzet, met nadruk op 'dubbel probleem'."""
    grootste = tabel["omzet"].max()

    def reeks(deel: pd.DataFrame, naam: str, kleur: str, open_marker: bool = False) -> go.Scatter:
        marker = dict(
            size=deel["omzet"], sizemode="area", sizeref=2 * grootste / (46**2), sizemin=5,
            color="rgba(0,0,0,0)" if open_marker else kleur, line=dict(color=kleur, width=1.5 if open_marker else 1),
        )
        if not open_marker:
            marker["opacity"] = 0.75
        return go.Scatter(
            x=deel["marge"], y=deel["pct_vertraagd"], mode="markers", name=naam, marker=marker,
            hovertext=[hover_tekst(r) for r in deel.itertuples()], hoverinfo="text",
        )

    doet = tabel[tabel["meedoen"]]
    fig = go.Figure()
    for problemen, kleur in ((0, GRIJS), (1, BLAUW), (2, ORANJE)):
        deel = doet[doet["problemen"] == problemen]
        fig.add_trace(reeks(deel, f"{pl.GROEPEN[problemen]} ({len(deel)})", kleur))
    uit = tabel[~tabel["meedoen"]]
    if len(uit):
        fig.add_trace(reeks(uit, f"Geen rang: te weinig orderlijnen ({len(uit)})", GRIJS, open_marker=True))

    fig.add_vline(x=totaal["marge"], line=dict(color=GRIJS, width=1, dash="dash"))
    fig.add_hline(y=totaal["pct_vertraagd"], line=dict(color=GRIJS, width=1, dash="dash"))
    hoeken = [
        (0.01, 0.99, "left", "top", "Lage marge, veel vertraging"),
        (0.99, 0.99, "right", "top", "Hoge marge, veel vertraging"),
        (0.01, 0.01, "left", "bottom", "Lage marge, weinig vertraging"),
        (0.99, 0.01, "right", "bottom", "Hoge marge, weinig vertraging"),
    ]
    for x, y, xanker, yanker, tekst in hoeken:
        fig.add_annotation(x=x, y=y, xref="paper", yref="paper", xanchor=xanker, yanchor=yanker, text=tekst,
                           showarrow=False, font=dict(size=11, color=GRIJS))
    fig.update_xaxes(title=f"Marge (winst / omzet); stippellijn = totaal {fmt_pct(totaal['marge'])}", tickformat=".0%",
                     showgrid=True, gridcolor=RASTER, zeroline=False)
    fig.update_yaxes(title=f"Percentage vertraagde orders; stippellijn = totaal {fmt_pct(totaal['pct_vertraagd'])}",
                     tickformat=".0%", showgrid=True, gridcolor=RASTER)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=90, b=10),
        height=620,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def dubbel_probleem_staven(ranglijst: pd.DataFrame, aantal: int) -> go.Figure:
    """Combinaties met twee problemen, gerangschikt op omzet; één kleur (nadruk)."""
    deel = ranglijst[ranglijst["problemen"] == 2].head(aantal)
    namen = [f"{int(r.rang)}. {r.categorie} · {r.markt}" for r in deel.itertuples()]
    fig = go.Figure(
        go.Bar(
            x=deel["omzet"], y=namen, orientation="h",
            marker=dict(color=ORANJE, cornerradius=4),
            text=[fmt_mln(v) for v in deel["omzet"]], textposition="outside", cliponaxis=False,
            hovertext=[hover_tekst(r) for r in deel.itertuples()], hoverinfo="text",
        )
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(showgrid=True, gridcolor=RASTER, title="Omzet (na korting)")
    fig.update_layout(
        title=dict(text=f"Combinaties met een dubbel probleem, op omzet (top {len(deel)})", x=0, font=dict(size=15)),
        bargap=0.5, showlegend=False, height=28 * len(deel) + 110,
        margin=dict(l=10, r=70, t=50, b=10), plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def trechter(stappen: list[pl.StapInfo]) -> go.Figure:
    namen = [s.naam for s in stappen]
    waarden = [s.rijen_uit for s in stappen]
    fig = go.Figure(go.Bar(x=waarden, y=namen, orientation="h", marker=dict(color=BLAUW, cornerradius=4),
                           text=[fmt_getal(n) for n in waarden], textposition="outside", cliponaxis=False, hoverinfo="skip"))
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(visible=False, type="log")  # 172.765 orderlijnen naast 69 combinaties: log-schaal
    fig.update_layout(height=300, bargap=0.5, margin=dict(l=10, r=60, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    return fig


# --------------------------------------------------------------------------- pagina's


@st.cache_resource(show_spinner="DV4 haalt DV1, DV2 en DV3 op...")
def laad_basis() -> pl.Basis:
    return pl.bouw_basis()


def toon_kpis(prio: pl.Prioriteit) -> None:
    k = prio.kpis
    a, b, c, d = st.columns(4)
    a.metric("Combinaties markt x categorie", fmt_getal(k["combinaties"]))
    b.metric("Doen mee in de rangschikking", fmt_getal(k["meedoen"]), help=f"Samen {fmt_pct(k['meedoen_omzetaandeel'])} van de omzet")
    c.metric("Met een dubbel probleem", fmt_getal(k["dubbel"]))
    d.metric("Omzetaandeel van die groep", fmt_pct(k["dubbel_omzetaandeel"]))


def tab_matrix(prio: pl.Prioriteit, totaal: dict) -> None:
    st.caption(
        "Elke bol is een combinatie van markt en categorie; de grootte is de omzet. Links van de verticale stippellijn ligt de marge onder het "
        "totaal, boven de horizontale stippellijn zijn er meer vertraagde orders dan gemiddeld. Linksboven (oranje) is het dubbele probleem."
    )
    st.plotly_chart(prioriteitenmatrix(prio.tabel, totaal), width="stretch")
    st.warning(
        "Lees dit als een volgorde om uit te zoeken, niet als een oordeel. Het verschil met het gemiddelde kan klein zijn, en een lage marge of "
        "veel vertraging zegt niets over de oorzaak. Een kleine afwijking (zie hover) kan gewoon toeval zijn."
    )


def tab_rangschikking(prio: pl.Prioriteit) -> None:
    st.caption("Eerst combinaties met twee problemen, dan met één, dan met geen. Binnen elke groep staat de grootste omzet vooraan.")
    dubbel = int(prio.kpis["dubbel"])
    if dubbel:
        aantal = st.slider("Aantal combinaties in de grafiek", 1, dubbel, min(10, dubbel))
        st.plotly_chart(dubbel_probleem_staven(prio.ranglijst, aantal), width="stretch")
    else:
        st.info("Bij deze drempel is er geen combinatie met een dubbel probleem.")
    st.subheader("Volledige ranglijst")
    toon = prio.ranglijst[
        ["rang", "markt", "categorie", "groep", "omzet", "omzetaandeel", "marge", "marge_verschil", "pct_vertraagd",
         "vertraging_verschil", "orderlijnen", "winstverschil", "kortingspct"]
    ]
    st.dataframe(
        toon, hide_index=True, width="stretch",
        column_config={
            "rang": st.column_config.NumberColumn("rang", format="%d"),
            "omzet": st.column_config.NumberColumn("omzet", format="%.0f"),
            "omzetaandeel": st.column_config.NumberColumn("omzetaandeel", format="percent"),
            "marge": st.column_config.NumberColumn("marge", format="percent"),
            "marge_verschil": st.column_config.NumberColumn("marge t.o.v. totaal", format="%+.3f"),
            "pct_vertraagd": st.column_config.NumberColumn("% vertraagd", format="percent"),
            "vertraging_verschil": st.column_config.NumberColumn("vertraging t.o.v. totaal", format="%+.3f"),
            "winstverschil": st.column_config.NumberColumn("winstverschil*", format="%.0f"),
            "kortingspct": st.column_config.NumberColumn("korting % (context)", format="percent"),
        },
    )
    st.caption(
        "*Winstverschil = omzet x (totale marge - eigen marge): een maat voor het gewicht van het margeverschil, **geen besparing**. "
        "De kolom 'korting' staat er enkel als context: DV3 vond geen verband tussen korting en marge, dus ze telt niet mee in de rang."
    )


def tab_tabel(prio: pl.Prioriteit) -> None:
    st.caption("Alle combinaties, ook die zonder rang (te weinig orderlijnen).")
    st.dataframe(
        prio.tabel.sort_values(["meedoen", "problemen", "omzet"], ascending=[False, False, False]),
        hide_index=True, width="stretch",
        column_config={
            "omzet": st.column_config.NumberColumn("omzet", format="%.0f"),
            "winst": st.column_config.NumberColumn("winst", format="%.0f"),
            "marge": st.column_config.NumberColumn("marge", format="percent"),
            "pct_vertraagd": st.column_config.NumberColumn("% vertraagd", format="percent"),
            "kortingspct": st.column_config.NumberColumn("korting %", format="percent"),
            "verlies_aandeel": st.column_config.NumberColumn("verlieslatend %", format="percent"),
            "omzetaandeel": st.column_config.NumberColumn("omzetaandeel", format="percent"),
            "winstverschil": st.column_config.NumberColumn("winstverschil*", format="%.0f"),
            "rang": st.column_config.NumberColumn("rang", format="%d"),
        },
    )


def tab_stappen(prio: pl.Prioriteit) -> None:
    for stap in prio.stappen:
        with st.expander(f"{stap.naam}: {fmt_getal(stap.rijen_in)} → {fmt_getal(stap.rijen_uit)} rijen"):
            st.write(f"**Waarom:** {stap.reden}")
            st.write("**Voorbeeld na deze stap (eerste 5 rijen):**")
            st.dataframe(stap.voorbeeld, hide_index=True)


def main() -> None:
    st.title("DV4: verbeterprioriteiten")
    st.write(
        "Welke combinaties van markt en categorie verdienen als eerste onderzoek? We combineren **marge** (DV1) en **vertraagde orders** (DV2): "
        "onder het totaal voor marge en boven het totaal voor vertraging telt als probleem. Zie `beslissingslogboek.md`."
    )
    try:
        basis = laad_basis()
    except FileNotFoundError as fout:
        st.error(str(fout))
        return

    drempel = st.select_slider(
        "Minimaal aantal orderlijnen per combinatie om mee te doen in de rangschikking",
        options=[30, 100, 200, 300, 500, 1000],
        value=pl.STANDAARD_MIN_LIJNEN,
        help="Onder ongeveer 300 lijnen is een marge grotendeels ruis. Combinaties eronder blijven zichtbaar maar krijgen geen rang.",
    )
    prio = pl.bereken_prioriteit(basis, drempel)
    toon_kpis(prio)
    st.subheader("Trechter: van orderlijnen naar de ranglijst")
    st.caption("Log-schaal: 172.765 orderlijnen naast enkele tientallen combinaties.")
    st.plotly_chart(trechter(prio.stappen), width="stretch")

    matrix, rang, tabel, stappen = st.tabs(["Prioriteitenmatrix", "Rangschikking", "Tabel", "Stappen"])
    with matrix:
        tab_matrix(prio, basis.totaal)
    with rang:
        tab_rangschikking(prio)
    with tabel:
        tab_tabel(prio)
    with stappen:
        tab_stappen(prio)


if __name__ == "__main__":
    st.set_page_config(page_title="DV4 Verbeterprioriteiten", layout="wide")
    main()
