"""DV1 — Omzet & Winst: real aggregates from the validated pipeline."""
import plotly.graph_objects as go
import streamlit as st

from analysis.kpis import MIN_ORDERS, financial_kpis
from ui.common import (C_PROFIT, C_REVENUE, QUESTIONS, evidence_panels, filter_banner, fmt_int, fmt_money, fmt_pct,
                       guard, insight_box, kpi_row, page_heading, style_figure)
from ui.data import get_scope

page_heading("DV1 · Omzet & Winst", QUESTIONS["DV1"])
scope = guard(get_scope())
fin = scope.fin
filter_banner(scope, f"{fmt_int(len(fin))} orderregels in de analysebasis")

total = financial_kpis(fin).iloc[0]
by_market = financial_kpis(fin, ["Market"]).sort_values("revenue", ascending=False)
by_mc = financial_kpis(fin, ["Market", "Category Name"])

kpi_row([
    ("Omzet (netto)", fmt_money(total["revenue"]), "Som van Order Item Total (na korting) · K-REV"),
    ("Winst", fmt_money(total["profit"]), "Som van Order Profit Per Order · K-PROFIT"),
    ("Gewogen winstmarge", fmt_pct(total["margin_pct"]), "100 × som winst / som omzet · K-MARGIN"),
    ("Orderregels", fmt_int(total["lines"]), f"Unieke orders: {fmt_int(total['orders'])} (orderregel ≠ order) · K-ORDERS"),
])

left, right = st.columns([1.0, 1.15])
with left:
    with st.container(border=True):
        st.subheader("Omzet en winst per markt")
        fig = go.Figure()
        fig.add_bar(name="Omzet", x=by_market["Market"], y=by_market["revenue"], marker_color=C_REVENUE,
                    hovertemplate="%{x}<br>Omzet: %{y:,.0f}<extra></extra>")
        fig.add_bar(name="Winst", x=by_market["Market"], y=by_market["profit"], marker_color=C_PROFIT,
                    customdata=by_market[["margin_pct", "lines", "orders"]],
                    hovertemplate="%{x}<br>Winst: %{y:,.0f}<br>Marge: %{customdata[0]:.1f}%<br>%{customdata[1]:,} regels · %{customdata[2]:,} orders<extra></extra>")
        fig.update_layout(barmode="group", yaxis_title="Bedrag (bronvaluta)")
        st.plotly_chart(style_figure(fig), width="stretch")
with right:
    with st.container(border=True):
        st.subheader("Winstmarge per markt × categorie")
        pivot = by_mc.pivot(index="Category Name", columns="Market", values="margin_pct")
        order = by_mc.groupby("Category Name")["revenue"].sum().sort_values(ascending=False).index
        pivot = pivot.reindex(order)
        counts = by_mc.pivot(index="Category Name", columns="Market", values="lines").reindex(order)
        heat = go.Figure(go.Heatmap(
            z=pivot.values, x=pivot.columns, y=pivot.index, colorscale="Purples", colorbar=dict(title="Marge %"),
            customdata=counts.values, hovertemplate="%{y} · %{x}<br>Marge: %{z:.1f}%<br>Orderregels: %{customdata:,}<extra></extra>",
        ))
        heat.update_yaxes(autorange="reversed")
        st.plotly_chart(style_figure(heat, height=max(380, 22 * len(pivot) + 80)), width="stretch")
        st.caption("Lege cel = combinatie komt niet voor in de selectie. Kleur toont alleen de hoogte van de marge, geen oordeel.")

# --- insights generated from the computed tables only ---
bullets = []
top = by_market.iloc[0]
share = 100 * top["revenue"] / total["revenue"]
bullets.append(f"**{top['Market']}** heeft de hoogste omzet ({fmt_money(top['revenue'])}, {fmt_pct(share)} van het totaal) en een marge van {fmt_pct(top['margin_pct'])}.")
if len(by_market) > 1:
    low = by_market.sort_values("margin_pct").iloc[0]
    high = by_market.sort_values("margin_pct").iloc[-1]
    bullets.append(f"Margeverschil tussen markten: laagste **{low['Market']}** ({fmt_pct(low['margin_pct'])}), hoogste **{high['Market']}** ({fmt_pct(high['margin_pct'])}).")
solid = by_mc[by_mc["orders"] >= MIN_ORDERS].sort_values("margin_pct")
if not solid.empty:
    r = solid.iloc[0]
    bullets.append(f"Laagste marge bij segmenten met ≥ {MIN_ORDERS} orders: **{r['Market']} · {r['Category Name']}** ({fmt_pct(r['margin_pct'])}, {fmt_int(r['orders'])} orders).")
neg = int((fin["Order Profit Per Order"] < 0).sum())
bullets.append(f"{fmt_int(neg)} orderregels ({fmt_pct(100 * neg / len(fin))}) hebben een negatieve winst; ze zijn bewust niet verwijderd.")
insight_box("Wat zien we?", bullets)

detail = by_mc.sort_values("revenue", ascending=False).rename(columns={
    "Market": "Markt", "Category Name": "Categorie", "revenue": "Omzet (netto)", "profit": "Winst", "margin_pct": "Marge %",
    "gross_sales": "Bruto Sales", "lines": "Orderregels", "orders": "Unieke orders"}).round(2)
n_in = len(scope.result.financial_rows)
evidence_panels(
    {
        "K-REV": dict(numerator=total["revenue"], denominator=None, result=total["revenue"], input_rows=n_in, analysis_rows=len(fin)),
        "K-PROFIT": dict(numerator=total["profit"], denominator=None, result=total["profit"], input_rows=n_in, analysis_rows=len(fin)),
        "K-MARGIN": dict(numerator=total["profit"], denominator=total["revenue"], result=total["margin_pct"], input_rows=n_in, analysis_rows=len(fin)),
        "K-ORDERS": dict(numerator=total["orders"], denominator=total["lines"], result=total["orders"], input_rows=n_in, analysis_rows=len(fin)),
    },
    scope, detail, file_stem="dv1_markt_categorie",
    notes=("Unieke orders per categorie tellen een order met meerdere categorieën in elke categorie; ze tellen dus niet op tot het totaal.",),
    sample=fin[["Order Id", "Order Item Id", "Market", "Category Name", "order_date", "Sales", "Order Item Total", "Order Profit Per Order"]],
)
