"""DV2 — Leverbetrouwbaarheid: % vertraagde orders on unique-order grain."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from analysis.kpis import MIN_ORDERS, delivery_kpis
from ui.common import (C_LATE, QUESTIONS, evidence_panels, filter_banner, fmt_int, fmt_pct, guard, insight_box,
                       kpi_row, page_heading, style_figure)
from ui.data import get_scope

page_heading("DV2 · Leverbetrouwbaarheid", QUESTIONS["DV2"])
scope = guard(get_scope())
ocs = scope.ocs
if ocs.empty:
    st.info("Geen orders voor deze filtercombinatie (alle KPI's = N/B).")
    st.stop()
filter_banner(scope, f"{fmt_int(ocs['Order Id'].nunique())} unieke orders in de selectie")

total = delivery_kpis(ocs).iloc[0]
by_market = delivery_kpis(ocs, ["Market"]).sort_values("late_pct", ascending=False)
by_mc = delivery_kpis(ocs, ["Market", "Category Name"])

kpi_row([
    ("Orders in aanmerking", fmt_int(total["eligible_orders"]), "Unieke orders zonder 'Shipping canceled' · noemer van K-LATEPCT"),
    ("Vertraagde orders", fmt_int(total["late_orders"]), "Unieke orders met Delivery Status = 'Late delivery' · teller"),
    ("% vertraagde orders", fmt_pct(total["late_pct"]), "100 × vertraagd / in aanmerking · K-LATEPCT"),
    ("Uitgesloten (geannuleerd)", fmt_int(total["excluded_orders"]), f"Aandeel van alle orders in de selectie: {fmt_pct(100 * total['excluded_orders'] / total['orders_all'])} · K-EXCL"),
])

left, right = st.columns([1.0, 1.15])
with left:
    with st.container(border=True):
        st.subheader("% vertraagde orders per markt")
        fig = go.Figure(go.Bar(
            x=by_market["Market"], y=by_market["late_pct"], marker_color=C_LATE,
            customdata=by_market[["late_orders", "eligible_orders"]],
            hovertemplate="%{x}<br>%{y:.1f}% vertraagd<br>%{customdata[0]:,} van %{customdata[1]:,} orders<extra></extra>",
            text=[fmt_pct(v) for v in by_market["late_pct"]], textposition="outside",
        ))
        fig.update_layout(yaxis_title="% vertraagde orders", yaxis_range=[0, 100])
        st.plotly_chart(style_figure(fig), width="stretch")
        st.caption("As start bij 0 om verschillen niet te overdrijven. Teller/noemer staan in de hover.")
with right:
    with st.container(border=True):
        st.subheader("% vertraagd per markt × categorie")
        enough = by_mc["eligible_orders"] >= MIN_ORDERS
        pct = by_mc["late_pct"].where(enough)
        piv = by_mc.assign(p=pct).pivot(index="Category Name", columns="Market", values="p")
        cnt = by_mc.pivot(index="Category Name", columns="Market", values="eligible_orders")
        order = by_mc.groupby("Category Name")["eligible_orders"].sum().sort_values(ascending=False).index
        piv, cnt = piv.reindex(order), cnt.reindex(order)
        heat = go.Figure(go.Heatmap(
            z=piv.values, x=piv.columns, y=piv.index, colorscale="Oranges", colorbar=dict(title="% laat"),
            customdata=cnt.values, hovertemplate="%{y} · %{x}<br>%{z:.1f}% vertraagd<br>%{customdata:,} orders<extra></extra>",
        ))
        heat.update_yaxes(autorange="reversed")
        st.plotly_chart(style_figure(heat, height=max(380, 22 * len(piv) + 80)), width="stretch")
        hidden = int((~enough).sum())
        st.caption(f"Cellen met minder dan {MIN_ORDERS} orders zijn leeg gelaten (onvoldoende data): {hidden} van {len(by_mc)} combinaties.")

bullets = []
if len(by_market) > 1:
    hi, lo = by_market.iloc[0], by_market.iloc[-1]
    gap = f"{hi['late_pct'] - lo['late_pct']:.1f}".replace(".", ",")
    bullets.append(f"Hoogste % vertraagd: **{hi['Market']}** ({fmt_pct(hi['late_pct'])}, {fmt_int(hi['late_orders'])} van {fmt_int(hi['eligible_orders'])}); "
                   f"laagste: **{lo['Market']}** ({fmt_pct(lo['late_pct'])}). Verschil: {gap} procentpunt.")
solid = by_mc[enough].sort_values("late_pct", ascending=False)
if not solid.empty:
    r = solid.iloc[0]
    bullets.append(f"Hoogste % bij segmenten met ≥ {MIN_ORDERS} orders: **{r['Market']} · {r['Category Name']}** ({fmt_pct(r['late_pct'])}, {fmt_int(r['eligible_orders'])} orders).")
bullets.append(f"Categorie-aantallen tellen niet op tot het ordertotaal: som over alle categorieën = {fmt_int(by_mc['eligible_orders'].sum())}, unieke orders = {fmt_int(total['eligible_orders'])} (een order met meerdere categorieën telt in elke categorie één keer).")
insight_box("Wat zien we?", bullets)

detail = by_mc.sort_values(["late_pct", "eligible_orders"], ascending=[False, False]).rename(columns={
    "Market": "Markt", "Category Name": "Categorie", "orders_all": "Alle orders", "eligible_orders": "In aanmerking",
    "late_orders": "Vertraagd", "excluded_orders": "Uitgesloten", "late_pct": "% vertraagd"}).round(2)
detail["Voldoende data"] = np.where(by_mc.loc[detail.index, "eligible_orders"] >= MIN_ORDERS, "ja", f"nee (< {MIN_ORDERS})")
n_in = len(scope.result.order_category_shipping)
evidence_panels(
    {
        "K-LATEPCT": dict(numerator=total["late_orders"], denominator=total["eligible_orders"], result=total["late_pct"], input_rows=n_in, analysis_rows=len(ocs)),
        "K-EXCL": dict(numerator=total["excluded_orders"], denominator=total["orders_all"], result=100 * total["excluded_orders"] / total["orders_all"], input_rows=n_in, analysis_rows=len(ocs)),
    },
    scope, detail, file_stem="dv2_markt_categorie",
    notes=("Rijen in deze verantwoording zijn order × markt × categorie-combinaties (niet orderregels).",
           "Geen enkele order heeft tegenstrijdige leverstatussen (pipeline stopt anders met een fout; geen stille first())."),
    sample=ocs[["Order Id", "Market", "Category Name", "order_date", "delivery_status", "is_late", "delivery_eligible"]],
)
