"""DV3 — Kortingen & Marges: descriptive association, never causality."""
import plotly.graph_objects as go
import streamlit as st

from analysis.kpis import (DISCOUNT_BINS, DISCOUNT_LABELS, PROFIT_COL, REVENUE_COL, deterministic_sample,
                           discount_margin_correlation, financial_kpis, margin_by_discount_class)
from ui.common import (C_MARGIN, QUESTIONS, evidence_panels, filter_banner, fmt_int, fmt_money, fmt_pct, guard,
                       insight_box, kpi_row, page_heading, style_figure)
from ui.data import get_scope

page_heading("DV3 · Kortingen & Marges", QUESTIONS["DV3"])
scope = guard(get_scope())
fin = scope.fin
filter_banner(scope, f"{fmt_int(len(fin))} orderregels in de analysebasis")

total = financial_kpis(fin).iloc[0]
weighted_discount = 100 * fin["Order Item Discount"].sum() / fin["Sales"].sum() if fin["Sales"].sum() > 0 else float("nan")
corr = discount_margin_correlation(fin)
classes = margin_by_discount_class(fin)

rho = corr["spearman"]
kpi_row([
    ("Gewogen kortingspercentage", fmt_pct(weighted_discount), "100 × som(Order Item Discount) / som(Sales) — gewogen op bruto verkoopwaarde"),
    ("Gewogen winstmarge", fmt_pct(total["margin_pct"]), "100 × som winst / som omzet (na korting) · K-MARGIN"),
    ("Correlatie (Spearman)", "N/B" if rho is None else f"{rho:+.2f}".replace(".", ","),
     f"Rangcorrelatie korting vs. regelmarge op {fmt_int(corr['n'])} orderregels. Pearson: {'N/B' if corr['pearson'] is None else format(corr['pearson'], '+.2f')}. Samenhang, geen oorzaak."),
    ("Orderregels", fmt_int(len(fin)), "Waarnemingen na filters (grain: orderregel)"),
])
st.caption("**Samenhang, geen oorzakelijk bewijs.** Korting en marge kunnen allebei door productmix of markt worden bepaald.")

left, right = st.columns([1.1, 1.0])
with left:
    with st.container(border=True):
        st.subheader("Korting versus marge per orderregel")
        sample = deterministic_sample(fin[fin[REVENUE_COL] > 0], n=5000, seed=42)
        fig = go.Figure(go.Scatter(   # gewone (SVG-)scatter: 5.000 punten zijn genoeg, en WebGL is niet in elke browser beschikbaar
            x=100 * sample["Order Item Discount Rate"], y=100 * sample[PROFIT_COL] / sample[REVENUE_COL], mode="markers",
            marker=dict(color=C_MARGIN, size=5, opacity=0.25),
            hovertemplate="Korting %{x:.0f}%<br>Regelmarge %{y:.1f}%<extra></extra>",
        ))
        fig.update_layout(xaxis_title="Kortingspercentage (%)", yaxis_title="Regelmarge (%)")
        st.plotly_chart(style_figure(fig), width="stretch")
        st.caption(f"Deterministische steekproef van {fmt_int(len(sample))} van {fmt_int(len(fin))} regels (random_state=42). Kortingen komen in stappen voor, dus punten vormen kolommen.")
with right:
    with st.container(border=True):
        st.subheader("Gewogen marge per kortingsklasse")
        fig = go.Figure(go.Bar(
            x=classes["discount_class"].astype(str), y=classes["margin_pct"], marker_color=C_MARGIN,
            customdata=classes[["lines", "revenue"]], text=[fmt_pct(v) for v in classes["margin_pct"]], textposition="outside",
            hovertemplate="Klasse %{x}<br>Marge %{y:.1f}%<br>%{customdata[0]:,} regels<extra></extra>",
        ))
        fig.update_layout(xaxis_title="Kortingsklasse", yaxis_title="Gewogen marge (%)")
        st.plotly_chart(style_figure(fig), width="stretch")
        st.caption("Klassegrenzen: zie D-009 in het logboek (goedgekeurd). Aantallen per klasse staan in de hover en in de tabel hieronder.")

bullets = []
valid = classes.dropna(subset=["margin_pct"])
if len(valid) >= 2:
    first, last = valid.iloc[0], valid.iloc[-1]
    bullets.append(f"Gewogen marge in klasse **{first['discount_class']}**: {fmt_pct(first['margin_pct'])} ({fmt_int(first['lines'])} regels); in klasse **{last['discount_class']}**: {fmt_pct(last['margin_pct'])} ({fmt_int(last['lines'])} regels).")
if rho is not None:
    strength = "zeer zwak" if abs(rho) < 0.1 else "zwak" if abs(rho) < 0.3 else "matig" if abs(rho) < 0.5 else "sterk"
    direction = "negatief" if rho < 0 else "positief"
    bullets.append(f"Spearman-correlatie tussen korting en regelmarge: {format(rho, '+.2f').replace('.', ',')} ({strength}, {direction}; n = {fmt_int(corr['n'])}). "
                   "Dit beschrijft samenhang, niet of korting de marge veroorzaakt.")
small = valid[valid["lines"] < 100]
if not small.empty:
    bullets.append("Klassen met minder dan 100 regels zijn wankel: " + ", ".join(f"{r['discount_class']} ({fmt_int(r['lines'])})" for _, r in small.iterrows()) + ".")
insight_box("Wat zien we?", bullets)

detail = classes.rename(columns={"discount_class": "Kortingsklasse", "revenue": "Omzet (netto)", "profit": "Winst", "margin_pct": "Gewogen marge %",
                                 "lines": "Orderregels", "orders": "Unieke orders", "gross_sales": "Bruto Sales"}).round(2)
detail["Kortingsklasse"] = detail["Kortingsklasse"].astype(str)
n_in = len(scope.result.financial_rows)
evidence_panels(
    {"K-DISC": dict(numerator=total["profit"], denominator=total["revenue"], result=corr["spearman"], input_rows=n_in, analysis_rows=len(fin)),
     "K-MARGIN": dict(numerator=total["profit"], denominator=total["revenue"], result=total["margin_pct"], input_rows=n_in, analysis_rows=len(fin))},
    scope, detail, file_stem="dv3_kortingsklassen",
    notes=(f"Kortingseenheid geaudit: min {scope.result.quality_report['discount_rate_min']}, max {scope.result.quality_report['discount_rate_max']} → fractie 0–1 ({scope.result.quality_report['discount_rate_unit']}); in de grafiek ×100. Geen dubbele omrekening.",
           f"Klassegrenzen (fractie): {list(DISCOUNT_BINS[1:])} → {list(DISCOUNT_LABELS)}. Goedgekeurd (D-009, logboek 9).",
           "Gewogen kortingspercentage = som(Order Item Discount) / som(Sales); dit verschilt van het gemiddelde van regelpercentages."),
    sample=fin[["Order Id", "Order Item Id", "Market", "Category Name", "Sales", "Order Item Discount", "Order Item Discount Rate", "Order Item Total", "Order Profit Per Order"]],
)
