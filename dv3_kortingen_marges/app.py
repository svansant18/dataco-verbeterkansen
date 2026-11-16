"""Sub-app DV3: kortingen en marges, het verband tussen kortingspercentage en gerealiseerde marge.

Alle berekeningen staan in `pipeline.py`; dit bestand toont enkel. Geen zijbalk (CLAUDE.md, afspraak 8).
De app toont een verband (correlatie), nooit een oorzaak.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dv3_kortingen_marges import pipeline as pl  # noqa: E402

BLAUW = "#2a78d6"  # reeks 1
GRIJS = "#898781"  # gedempt: trendlijn en groepen met weinig data
RASTER = "rgba(128,128,128,0.25)"  # recessief raster, werkt in licht en donker


# --------------------------------------------------------------------------- opmaak


def fmt_getal(n: float) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,.0f}".replace(",", ".")


def fmt_pct(x: float, decimalen: int = 1) -> str:
    """0.1203 -> '12,0%'."""
    return f"{x * 100:.{decimalen}f}".replace(".", ",") + "%"


def fmt_r(r: float) -> str:
    """-0.0829 -> '-0,08'."""
    return f"{r:.2f}".replace(".", ",")


# --------------------------------------------------------------------------- grafieken


def staafdiagram(tabel: pd.DataFrame, x: str, y: str, titel: str) -> go.Figure:
    """Staven in de volgorde van de klassen, in één kleur, met direct label. Y-as begint bij 0."""
    hover = [
        f"<b>{klasse}</b><br>Marge: {fmt_pct(m)}<br>Verlieslatende lijnen: {fmt_pct(v)}<br>Orderlijnen: {fmt_getal(n)}"
        for klasse, m, v, n in zip(tabel[x], tabel["marge"], tabel["verlies_aandeel"], tabel["orderlijnen"])
    ]
    fig = go.Figure(
        go.Bar(
            x=tabel[x],
            y=tabel[y],
            marker=dict(color=BLAUW, cornerradius=4),
            text=[fmt_pct(v) for v in tabel[y]],
            textposition="outside",
            cliponaxis=False,
            hovertext=hover,
            hoverinfo="text",
        )
    )
    fig.update_xaxes(title="Kortingsklasse")
    fig.update_yaxes(showgrid=True, gridcolor=RASTER, title=None, tickformat=".0%", range=[0, max(tabel[y]) * 1.3])
    fig.update_layout(
        title=dict(text=titel, x=0, font=dict(size=15)),
        bargap=0.55,
        showlegend=False,  # één reeks: de titel benoemt ze
        margin=dict(l=10, r=10, t=50, b=10),
        height=340,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def scatter(
    tabel: pd.DataFrame, verband: dict, titel: str, punt_naam: str, hover_namen, grootte_naar_lijnen: bool, y_vanaf_nul: bool
) -> go.Figure:
    """Korting (x) tegen marge (y), met trendlijn en een legenda voor de reeksen."""

    def punten(deel: pd.DataFrame, naam: str, kleur: str, open_marker: bool) -> go.Scatter:
        if grootte_naar_lijnen:
            grootte = dict(size=deel["orderlijnen"], sizemode="area", sizeref=2 * tabel["orderlijnen"].max() / (34**2), sizemin=5)
        else:
            grootte = dict(size=12)
        marker = dict(**grootte, color="rgba(0,0,0,0)" if open_marker else kleur, line=dict(color=kleur, width=1.5 if open_marker else 1))
        if not open_marker:
            marker["opacity"] = 0.75
        hover = [
            f"<b>{hover_namen(rij)}</b><br>Kortingspercentage: {fmt_pct(rij.kortingspct)}<br>Marge: {fmt_pct(rij.marge)}"
            f"<br>Verlieslatende lijnen: {fmt_pct(rij.verlies_aandeel)}<br>Orderlijnen: {fmt_getal(rij.orderlijnen)}"
            for rij in deel.itertuples()
        ]
        return go.Scatter(x=deel["kortingspct"], y=deel["marge"], mode="markers", name=naam, marker=marker,
                          hovertext=hover, hoverinfo="text")

    groot = tabel[~tabel["weinig_data"]]
    klein = tabel[tabel["weinig_data"]]
    fig = go.Figure(punten(groot, punt_naam, BLAUW, False))
    if len(klein):
        fig.add_trace(punten(klein, f"Weinig data (< {pl.MIN_LIJNEN} orderlijnen)", GRIJS, True))
    x0, x1 = tabel["kortingspct"].min(), tabel["kortingspct"].max()
    fig.add_trace(
        go.Scatter(
            x=[x0, x1],
            y=[verband["intercept"] + verband["helling"] * x0, verband["intercept"] + verband["helling"] * x1],
            mode="lines",
            name="Trendlijn (ongewogen)",
            line=dict(color=GRIJS, width=2, dash="dash"),
            hoverinfo="skip",
        )
    )
    fig.update_xaxes(title="Kortingspercentage", tickformat=".0%", showgrid=True, gridcolor=RASTER)
    fig.update_yaxes(title="Marge (winst / omzet)", tickformat=".0%", showgrid=True, gridcolor=RASTER,
                     range=[0, 0.25] if y_vanaf_nul else None, zeroline=True, zerolinecolor=RASTER)
    fig.update_layout(
        title=dict(text=titel, x=0, font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=90, b=10),
        height=480,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# --------------------------------------------------------------------------- pagina's


@st.cache_resource(show_spinner="DV3 rekent...")
def draai_dv3() -> pl.DV3Resultaat:
    return pl.run_dv3()


def toon_kpis(totaal: dict) -> None:
    a, b, c, d = st.columns(4)
    a.metric("Orderlijnen", fmt_getal(totaal["orderlijnen"]))
    b.metric("Gemiddelde korting (gewogen)", fmt_pct(totaal["kortingspct"]))
    c.metric("Marge (winst / omzet)", fmt_pct(totaal["marge"]))
    d.metric("Verlieslatende lijnen", fmt_pct(totaal["verlies_aandeel"]), help="Aandeel orderlijnen met negatieve winst")


def toon_trechter(stappen: list[pl.StapInfo]) -> None:
    st.subheader("Trechter: van orderlijnen naar groepen")
    st.caption("Rijen na elke stap. Stap 4 tot 6 vatten dezelfde orderlijnen op een ander niveau samen.")
    namen = [s.naam for s in stappen]
    waarden = [s.rijen_uit for s in stappen]
    fig = go.Figure(go.Bar(x=waarden, y=namen, orientation="h", marker=dict(color=BLAUW, cornerradius=4),
                           text=[fmt_getal(n) for n in waarden], textposition="outside", cliponaxis=False, hoverinfo="skip"))
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(visible=False)
    fig.update_layout(height=290, bargap=0.5, margin=dict(l=10, r=60, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")


def toon_conclusie(res: pl.DV3Resultaat) -> None:
    n, c = res.verband_niveau, res.verband_combinatie
    # Over de 18 niveaus (0 tot 25%) is de helling betrouwbaar genoeg om in woorden te zetten.
    per_10pp = n["helling"] * 10  # procentpunt marge per 10 procentpunt extra korting
    richting = "lager" if per_10pp < 0 else "hoger"
    effect = f"{abs(per_10pp):.2f}".replace(".", ",")
    klein = " (praktisch niets)" if abs(per_10pp) < 0.5 else ""
    st.info(
        f"**Bevinding:** tussen kortingspercentage en marge is {pl.beschrijf_verband(n['r'])} te zien over de "
        f"{n['n']} kortingsniveaus (r = {fmt_r(n['r'])}) en {pl.beschrijf_verband(c['r'])} over de {c['n']} combinaties van "
        f"markt en categorie (r = {fmt_r(c['r'])}; zonder groepen met weinig data r = {fmt_r(c['r_zonder_klein'])}). "
        f"Over de kortingsniveaus is de marge gemiddeld {effect} procentpunt {richting} per 10 procentpunt extra korting{klein}. "
        "Een correlatie is geen oorzaak, en deze data bewijst niets over wat er zou gebeuren als je de korting verandert."
    )


def tab_niveau(res: pl.DV3Resultaat) -> None:
    st.caption(
        "Elk punt is één van de 18 kortingspercentages in de data (0% tot 25%), met de gewogen marge van alle orderlijnen "
        "met dat percentage. De y-as begint bewust bij 0%, zodat je ziet hoe klein de verschillen zijn."
    )
    fig = scatter(res.per_niveau, res.verband_niveau, "Marge per kortingsniveau", "Kortingsniveau",
                  lambda rij: f"Korting {fmt_pct(rij.niveau, 0)}", grootte_naar_lijnen=False, y_vanaf_nul=True)
    st.plotly_chart(fig, width="stretch")
    marges = res.per_niveau["marge"]
    st.write(f"De marge ligt per kortingsniveau tussen {fmt_pct(marges.min())} en {fmt_pct(marges.max())}, met r = {fmt_r(res.verband_niveau['r'])}.")


def tab_combinatie(res: pl.DV3Resultaat) -> None:
    st.caption(
        "Elk punt is één combinatie van markt en categorie: het gewogen kortingspercentage (som korting / som bruto omzet) tegen de gewogen "
        "marge. Grootte = aantal orderlijnen. Open grijze punten hebben weinig data."
    )
    fig = scatter(res.per_combinatie, res.verband_combinatie, "Marge tegen korting per markt en categorie", "Markt x categorie",
                  lambda rij: f"{rij.categorie} · {rij.markt}", grootte_naar_lijnen=True, y_vanaf_nul=False)
    st.plotly_chart(fig, width="stretch")
    k = res.per_combinatie["kortingspct"]
    st.write(
        f"Het gewogen kortingspercentage ligt per combinatie tussen {fmt_pct(k.min())} en {fmt_pct(k.max())}: een smal bereik. "
        "De marge varieert veel meer dan de korting, dus waar de marge van een combinatie vandaan komt, verklaart de korting hier niet."
    )


def tab_klassen(res: pl.DV3Resultaat) -> None:
    st.caption("Zes kortingsklassen van gelijke breedte, met 'geen korting' apart. Beide grafieken beginnen bij 0%.")
    links, rechts = st.columns(2)
    with links:
        st.plotly_chart(staafdiagram(res.per_klasse, "kortingsklasse", "marge", "Marge per kortingsklasse"), width="stretch")
    with rechts:
        st.plotly_chart(staafdiagram(res.per_klasse, "kortingsklasse", "verlies_aandeel", "Verlieslatende lijnen per kortingsklasse"),
                        width="stretch")
    m, v = res.per_klasse["marge"], res.per_klasse["verlies_aandeel"]
    st.write(
        f"De marge ligt per klasse tussen {fmt_pct(m.min())} en {fmt_pct(m.max())}; het aandeel verlieslatende orderlijnen tussen "
        f"{fmt_pct(v.min())} en {fmt_pct(v.max())}."
    )


def tab_tabel(res: pl.DV3Resultaat) -> None:
    keuzes = {
        "kortingsklasse": res.per_klasse,
        "kortingsniveau": res.per_niveau,
        "markt x categorie": res.per_combinatie,
    }
    niveau = st.radio("Detail", list(keuzes), horizontal=True)
    st.dataframe(
        keuzes[niveau],
        hide_index=True,
        width="stretch",
        column_config={
            "bruto": st.column_config.NumberColumn("bruto omzet", format="%.0f"),
            "omzet": st.column_config.NumberColumn("omzet na korting", format="%.0f"),
            "korting": st.column_config.NumberColumn("korting", format="%.0f"),
            "winst": st.column_config.NumberColumn("winst", format="%.0f"),
            "marge": st.column_config.NumberColumn("marge", format="percent"),
            "kortingspct": st.column_config.NumberColumn("korting %", format="percent"),
            "verlies_aandeel": st.column_config.NumberColumn("verlieslatend %", format="percent"),
            "weinig_data": st.column_config.CheckboxColumn(f"< {pl.MIN_LIJNEN} lijnen"),
        },
    )


def tab_stappen(res: pl.DV3Resultaat) -> None:
    for stap in res.stappen:
        with st.expander(f"{stap.naam}: {fmt_getal(stap.rijen_in)} → {fmt_getal(stap.rijen_uit)} rijen"):
            st.write(f"**Waarom:** {stap.reden}")
            st.write("**Voorbeeld na deze stap (eerste 5 rijen):**")
            st.dataframe(stap.voorbeeld, hide_index=True)


def main() -> None:
    st.title("DV3: kortingen en marges")
    st.write(
        "Is er een verband tussen het kortingspercentage en de gerealiseerde marge? Marge is **som winst / som omzet na korting**. "
        "Geannuleerde en fraude-orders zijn uitgesloten. Zie `beslissingslogboek.md`."
    )
    try:
        res = draai_dv3()
    except FileNotFoundError as fout:
        st.error(str(fout))
        return
    toon_kpis(res.totaal)
    toon_conclusie(res)
    toon_trechter(res.stappen)
    niveau, combinatie, klassen, tabel, stappen = st.tabs(
        ["Kortingsniveaus", "Markt x categorie", "Kortingsklassen", "Tabel", "Stappen"]
    )
    with niveau:
        tab_niveau(res)
    with combinatie:
        tab_combinatie(res)
    with klassen:
        tab_klassen(res)
    with tabel:
        tab_tabel(res)
    with stappen:
        tab_stappen(res)


if __name__ == "__main__":
    st.set_page_config(page_title="DV3 Kortingen en marges", layout="wide")
    main()
