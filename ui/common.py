"""Reusable page layout, formatting and evidence panels for DataCo's six pages."""
from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis.evidence import KPI_REGISTER
from ui.data import Scope

CENTRAL_QUESTION = (
    "Welke markten en productcategorieën bieden DataCo de grootste verbetermogelijkheden "
    "wanneer we omzet, winstgevendheid en leverbetrouwbaarheid samen analyseren?"
)
QUESTIONS = {
    "DV1": "Welke markten en productcategorieën realiseren de hoogste omzet en winst, en waar blijven de marges achter?",
    "DV2": "Welke markten en productcategorieën hebben het hoogste percentage vertraagde verzendingen?",
    "DV3": "In welke mate hangen kortingspercentages samen met de gerealiseerde winstmarges?",
    "DV4": "Welke combinaties van markt en productcategorie verdienen prioriteit op basis van hun commerciële prestaties en operationele risico's?",
}

# Consistent colours across pages: revenue blue, profit teal, margin violet, delay amber/red.
C_REVENUE, C_PROFIT, C_MARGIN, C_LATE = "#2563EB", "#0D9488", "#7C3AED", "#D97706"
NB = "N/B"
NOTHING_TO_COMPARE = ("Je filtert op één markt én één categorie: er is maar één segment, dus er valt niets te vergelijken. "
                      "Kies 'Alle markten' of 'Alle categorieën' om te vergelijken.")


# ---- formatting (Dutch separators; never show a made-up number) ----------------------------------
def _ok(x) -> bool:
    return x is not None and not (isinstance(x, float) and math.isnan(x)) and not pd.isna(x)


def fmt_int(x) -> str:
    return f"{int(x):,}".replace(",", ".") if _ok(x) else NB


def fmt_money(x) -> str:
    if not _ok(x):
        return NB
    x = float(x)
    if abs(x) >= 1_000_000:
        return f"{x / 1_000_000:,.2f} M".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{x:,.0f}".replace(",", ".")


def fmt_pct(x, digits: int = 1) -> str:
    return f"{float(x):.{digits}f}%".replace(".", ",") if _ok(x) else NB


# ---- layout ---------------------------------------------------------------------------------------
def page_heading(title: str, question: str) -> None:
    st.title(title)
    st.caption(question)


def kpi_row(items: list[tuple[str, str, str]]) -> None:
    """items: (label, formatted value, help text). Max four cards per page."""
    for column, (label, value, help_text) in zip(st.columns(len(items)), items):
        column.metric(label, value, help=help_text)


def filter_banner(scope: Scope, population: str) -> None:
    f = ", ".join(f"{k}: **{v}**" for k, v in scope.filters.as_pairs())
    st.caption(f"Actieve filters — {f} · {population}")


def guard(scope: Scope | None) -> Scope:
    """Stop the page with a clear message instead of showing fake or broken output."""
    if scope is None:
        st.warning("Geen bron gevonden: plaats precies één DataCo-CSV onder `data/raw/`. Er worden geen cijfers getoond.")
        st.stop()
    if scope.empty:
        st.info("Geen data voor deze filtercombinatie (alle KPI's = N/B). Pas de filters aan of reset ze bovenaan.")
        st.stop()
    return scope


def style_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=36, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.12, x=0), font=dict(size=13))
    return fig


def insight_box(title: str, bullets: list[str]) -> None:
    with st.container(border=True):
        st.subheader(title)
        for b in bullets:
            st.markdown(f"- {b}")


# ---- evidence -------------------------------------------------------------------------------------
def evidence_panels(
    calc: dict[str, dict], scope: Scope, table: pd.DataFrame, *,
    notes: tuple[str, ...] = (), sample: pd.DataFrame | None = None, file_stem: str = "dataco",
) -> None:
    """The two mandatory evidence expanders of every DV.

    calc: {kpi_id: dict(numerator, denominator, result, input_rows, analysis_rows)} for the numbers on the page.
    """
    manifest = scope.result.source_manifest
    with st.expander("🔎 Hoe is dit berekend? · Bron, formule en controles"):
        for kpi_id, values in calc.items():
            d = KPI_REGISTER[kpi_id]
            st.markdown(f"#### {d['label']} · `{kpi_id}`")
            st.markdown(
                f"- **WAT:** {d['formula']} · eenheid: {d['unit']}\n"
                f"- **WAAR:** bronkolommen `{'`, `'.join(d['source_columns'])}` · grain: {d['grain']} · pipeline: {' → '.join(d['pipeline_stages'])}\n"
                f"- **HOEVEEL:** {fmt_int(values['analysis_rows'])} van {fmt_int(values['input_rows'])} rijen in de selectie"
                f" · teller: {fmt_num(values.get('numerator'))} ({d['numerator']}) · noemer: {fmt_num(values.get('denominator'))} ({d['denominator']})\n"
                f"- **WAAROM:** beslissing `{d['decision_id']}` · ontbrekend/nul: {d['missing_rule']}\n"
                f"- **CONTROLE:** {'; '.join(t.split('::')[-1] for t in d['test_ids'])}\n"
                f"- **Let op:** {d['caveat']}"
            )
        st.markdown("**Actieve filters:** " + " · ".join(f"{k}: {v}" for k, v in scope.filters.as_pairs()))
        st.caption(f"Bron: `{manifest['source_file']}` · SHA-256 `{manifest['source_sha256'][:16]}…` (ongewijzigd na de run)")
        for n in notes:
            st.markdown(f"- {n}")
    with st.expander("📋 Onderliggende data · Geaggregeerd en privacyveilig"):
        st.caption(f"{fmt_int(len(table))} rijen · geen namen, adressen, e-mails of wachtwoorden: die kolommen worden nooit ingelezen.")
        st.dataframe(table, width="stretch", hide_index=True)
        st.download_button("Download deze aggregatie (CSV)", table.to_csv(index=False).encode("utf-8"), f"{file_stem}.csv", "text/csv")
        if sample is not None and not sample.empty:
            st.markdown("**Voorbeeldregels uit de selectie** (eerste 10, enkel zakelijke kolommen):")
            st.dataframe(sample.head(10), width="stretch", hide_index=True)


def fmt_num(x) -> str:
    if not _ok(x):
        return "—"
    x = float(x)
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if x != int(x) else fmt_int(x)
