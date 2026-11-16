"""Sub-app DV2: leverbetrouwbaarheid, percentage vertraagde unieke orders.

Alle berekeningen staan in `pipeline.py`; dit bestand toont enkel. Geen zijbalk (CLAUDE.md, afspraak 8).
Kleur volgt dezelfde betekenis als DV1: blauw is beter dan het totaal (minder vertraagd), rood slechter.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dv2_leverbetrouwbaarheid import pipeline as pl  # noqa: E402

BLAUW = "#2a78d6"  # omvang, en 'beter dan gemiddeld' op de heatmap
ROOD = "#e34948"  # 'slechter dan gemiddeld' op de heatmap
GRIJS_MIDDEN = "#f0efec"  # neutraal midden van de divergerende schaal
RASTER = "rgba(128,128,128,0.25)"  # recessief raster, werkt in licht en donker


# --------------------------------------------------------------------------- opmaak


def fmt_getal(n: float) -> str:
    """12345 -> '12.345' (Vlaamse duizendtallen)."""
    return f"{n:,.0f}".replace(",", ".")


def fmt_pct(x: float) -> str:
    """0.5731 -> '57,3%'."""
    return f"{x * 100:.1f}".replace(".", ",") + "%"


# --------------------------------------------------------------------------- grafieken


def staafdiagram(tabel: pd.DataFrame, naam_kolom: str, meting: str, titel: str, horizontaal: bool = False) -> go.Figure:
    """Gerangschikte staven in één kleur; elke waarde heeft een direct label."""
    tabel = tabel.sort_values(meting, ascending=False)
    teksten = [fmt_pct(v) if meting == "pct_vertraagd" else fmt_getal(v) for v in tabel[meting]]
    hover = [
        f"<b>{naam}</b><br>Vertraagd: {fmt_pct(p)}<br>Orders: {fmt_getal(o)}<br>Vertraagde orders: {fmt_getal(v)}"
        + (f"<br><i>weinig data (&lt; {pl.MIN_ORDERS} orders)</i>" if w else "")
        for naam, p, o, v, w in zip(
            tabel[naam_kolom], tabel["pct_vertraagd"], tabel["orders"], tabel["vertraagd"], tabel["weinig_data"]
        )
    ]
    staaf = dict(
        marker=dict(color=BLAUW, cornerradius=4),
        text=teksten,
        textposition="outside",
        cliponaxis=False,
        hovertext=hover,
        hoverinfo="text",
    )
    procent = meting == "pct_vertraagd"
    if horizontaal:
        fig = go.Figure(go.Bar(x=tabel[meting], y=tabel[naam_kolom], orientation="h", **staaf))
        fig.update_yaxes(autorange="reversed", title=None)
        fig.update_xaxes(showgrid=True, gridcolor=RASTER, title=None, tickformat=".0%" if procent else None,
                         range=[0, 1.05] if procent else None)
        hoogte = 24 * len(tabel) + 80
    else:
        fig = go.Figure(go.Bar(x=tabel[naam_kolom], y=tabel[meting], **staaf))
        fig.update_xaxes(title=None)
        fig.update_yaxes(showgrid=True, gridcolor=RASTER, title=None, tickformat=".0%" if procent else None,
                         range=[0, 1.1] if procent else None)
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


def risico_heatmap(
    tabel: pd.DataFrame, rij: str, kolom: str, rijen: list[str], kolommen: list[str], totaal: float
) -> go.Figure:
    """Percentage vertraagd per rij en kolom; kleur t.o.v. het totaal (rood = vaker vertraagd)."""
    cellen = tabel.set_index([rij, kolom])

    def cel(r: str, k: str, veld: str):
        return cellen[veld].get((r, k))

    z, tekst, hover = [], [], []
    for r in rijen:
        z_rij, t_rij, h_rij = [], [], []
        for k in kolommen:
            pct = cel(r, k, "pct_vertraagd")
            if pct is None:
                z_rij.append(None)
                t_rij.append("")
                h_rij.append("")
                continue
            orders = int(cel(r, k, "orders"))
            weinig = orders < pl.MIN_ORDERS
            z_rij.append(pct)
            t_rij.append(fmt_pct(pct) + ("*" if weinig else ""))
            h_rij.append(
                f"<b>{r}</b> · {k}<br>Vertraagd: {fmt_pct(pct)}<br>Orders: {fmt_getal(orders)}"
                f"<br>Vertraagde orders: {fmt_getal(cel(r, k, 'vertraagd'))}" + (" (weinig data)" if weinig else "")
            )
        z.append(z_rij)
        tekst.append(t_rij)
        hover.append(h_rij)

    afwijking = max(abs(v - totaal) for rij_z in z for v in rij_z if v is not None)
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=kolommen,
            y=rijen,
            text=tekst,
            texttemplate="%{text}",
            hovertext=hover,
            hoverinfo="text",
            hoverongaps=False,
            zmid=totaal,
            zmin=totaal - afwijking,
            zmax=totaal + afwijking,
            colorscale=[[0, BLAUW], [0.5, GRIJS_MIDDEN], [1, ROOD]],
            xgap=2,
            ygap=2,
            colorbar=dict(title="Vertraagd", tickformat=".0%", thickness=12),
        )
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(side="top", title=None)
    fig.update_layout(
        height=max(24 * len(rijen) + 120, 260),
        margin=dict(l=10, r=10, t=60, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# --------------------------------------------------------------------------- pagina's


@st.cache_resource(show_spinner="DV2 rekent...")
def draai_dv2() -> pl.DV2Resultaat:
    return pl.run_dv2()


def toon_kpis(totaal: dict) -> None:
    a, b, c = st.columns(3)
    a.metric("Unieke orders", fmt_getal(totaal["orders"]))
    b.metric("Vertraagde orders", fmt_getal(totaal["vertraagd"]))
    c.metric("Percentage vertraagd", fmt_pct(totaal["pct_vertraagd"]))


def toon_trechter(stappen: list[pl.StapInfo]) -> None:
    st.subheader("Trechter: van orderlijnen naar orders")
    st.caption("Rijen na elke stap. Stap 3 en 4 beginnen allebei bij de orderlijnen: stap 3 telt orders, stap 4 order-categorieparen.")
    namen = [s.naam for s in stappen]
    waarden = [s.rijen_uit for s in stappen]
    fig = go.Figure(go.Bar(x=waarden, y=namen, orientation="h", marker=dict(color=BLAUW, cornerradius=4),
                           text=[fmt_getal(n) for n in waarden], textposition="outside", cliponaxis=False, hoverinfo="skip"))
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_xaxes(visible=False)
    fig.update_layout(height=220, bargap=0.5, margin=dict(l=10, r=60, t=10, b=10), plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")


def tab_markt(res: pl.DV2Resultaat) -> None:
    st.caption("Percentage orders dat te laat geleverd werd, per markt. Een order telt één keer, ongeacht het aantal orderlijnen.")
    links, rechts = st.columns(2)
    with links:
        st.plotly_chart(staafdiagram(res.per_markt, "markt", "pct_vertraagd", "Percentage vertraagd per markt"), width="stretch")
    with rechts:
        st.plotly_chart(staafdiagram(res.per_markt, "markt", "orders", "Aantal orders per markt"), width="stretch")
    p = res.per_markt["pct_vertraagd"]
    st.info(
        f"Per markt ligt het percentage vertraagd tussen {fmt_pct(p.min())} en {fmt_pct(p.max())} "
        f"(verschil {(p.max() - p.min()) * 100:.1f} procentpunt): de markten verschillen nauwelijks. "
        "Kijk ook naar het tabblad Verzendmethode."
    )


def tab_categorie(res: pl.DV2Resultaat) -> None:
    meting = st.radio("Rangschik de categorieën op", ["pct_vertraagd", "orders"], horizontal=True,
                      format_func=lambda m: "percentage vertraagd" if m == "pct_vertraagd" else "aantal orders")
    titel = "Percentage vertraagd per categorie" if meting == "pct_vertraagd" else "Aantal orders per categorie"
    st.plotly_chart(staafdiagram(res.per_categorie, "categorie", meting, titel, horizontaal=True), width="stretch")
    st.caption("Een order met producten uit meerdere categorieën telt in elke categorie mee; de som van de orders is daarom groter dan het totaal.")


def tab_heatmap(res: pl.DV2Resultaat) -> None:
    volgorde = st.radio("Sorteer de categorieën op", ["aantal orders", "percentage vertraagd"], horizontal=True)
    cat = res.per_categorie
    cat = cat if volgorde == "aantal orders" else cat.sort_values("pct_vertraagd", ascending=False)
    st.caption(
        f"Kleur toont het percentage vertraagd ten opzichte van het totaal ({fmt_pct(res.totaal['pct_vertraagd'])}): "
        f"rood is vaker vertraagd, blauw minder vaak, grijs ongeveer gelijk. Een * betekent minder dan {pl.MIN_ORDERS} orders: "
        "lees die waarde voorzichtig. Lege cellen: die combinatie komt niet voor in de data."
    )
    fig = risico_heatmap(res.per_combinatie, "categorie", "markt", list(cat["categorie"]), list(res.per_markt["markt"]),
                         res.totaal["pct_vertraagd"])
    st.plotly_chart(fig, width="stretch")


def tab_verzendmethode(res: pl.DV2Resultaat) -> None:
    st.caption("Extra invalshoek: het percentage vertraagd per verzendmethode, en per markt en verzendmethode.")
    links, rechts = st.columns(2)
    with links:
        st.plotly_chart(staafdiagram(res.per_verzendmethode, "verzendmethode", "pct_vertraagd", "Percentage vertraagd per verzendmethode"),
                        width="stretch")
    with rechts:
        st.plotly_chart(staafdiagram(res.per_verzendmethode, "verzendmethode", "orders", "Aantal orders per verzendmethode"),
                        width="stretch")
    methode = res.per_verzendmethode.set_index("verzendmethode")["pct_vertraagd"]
    st.info(
        f"Het verschil zit in de verzendmethode, niet in de markt: {', '.join(f'{m} {fmt_pct(p)}' for m, p in methode.sort_values(ascending=False).items())}. "
        "Dit zegt nog niets over de oorzaak. De data toont enkel dat de vlag per verzendmethode sterk verschilt."
    )
    st.plotly_chart(
        risico_heatmap(res.per_markt_verzendmethode, "markt", "verzendmethode", list(res.per_markt["markt"]),
                       list(res.per_verzendmethode["verzendmethode"]), res.totaal["pct_vertraagd"]),
        width="stretch",
    )


def tab_tabel(res: pl.DV2Resultaat) -> None:
    keuzes = {
        "markt x categorie": res.per_combinatie,
        "markt": res.per_markt,
        "categorie": res.per_categorie,
        "verzendmethode": res.per_verzendmethode,
        "markt x verzendmethode": res.per_markt_verzendmethode,
    }
    niveau = st.radio("Detail", list(keuzes), horizontal=True)
    st.dataframe(
        keuzes[niveau],
        hide_index=True,
        width="stretch",
        column_config={
            "pct_vertraagd": st.column_config.NumberColumn("% vertraagd", format="percent"),
            "weinig_data": st.column_config.CheckboxColumn(f"< {pl.MIN_ORDERS} orders"),
        },
    )
    if "categorie" in niveau:
        st.caption("Een order met meerdere categorieën telt in elke categorie mee, daarom is de som van `orders` groter dan het aantal unieke orders.")


def tab_stappen(res: pl.DV2Resultaat) -> None:
    for stap in res.stappen:
        with st.expander(f"{stap.naam}: {fmt_getal(stap.rijen_in)} → {fmt_getal(stap.rijen_uit)} rijen"):
            st.write(f"**Waarom:** {stap.reden}")
            st.write("**Voorbeeld na deze stap (eerste 5 rijen):**")
            st.dataframe(stap.voorbeeld, hide_index=True)


def main() -> None:
    st.title("DV2: leverbetrouwbaarheid")
    st.write(
        "Percentage **vertraagde unieke orders** (levering later dan gepland). Een order telt één keer, ongeacht het aantal "
        "orderlijnen. Geannuleerde en fraude-orders zijn uitgesloten. Zie `beslissingslogboek.md`."
    )
    try:
        res = draai_dv2()
    except FileNotFoundError as fout:
        st.error(str(fout))
        return
    toon_kpis(res.totaal)
    toon_trechter(res.stappen)
    markt, categorie, heatmap, methode, tabel, stappen = st.tabs(
        ["Per markt", "Per categorie", "Risico-heatmap", "Verzendmethode", "Tabel", "Stappen"]
    )
    with markt:
        tab_markt(res)
    with categorie:
        tab_categorie(res)
    with heatmap:
        tab_heatmap(res)
    with methode:
        tab_verzendmethode(res)
    with tabel:
        tab_tabel(res)
    with stappen:
        tab_stappen(res)


if __name__ == "__main__":
    st.set_page_config(page_title="DV2 Leverbetrouwbaarheid", layout="wide")
    main()
