"""Executive Overview: every number comes from the validated pipeline and the shared filters."""
import plotly.graph_objects as go
import streamlit as st

from analysis.kpis import RISK_CLASSES, comparison_dimension, delivery_kpis, financial_kpis, nothing_to_compare
from ui.common import (C_PROFIT, C_REVENUE, CENTRAL_QUESTION, NOTHING_TO_COMPARE, filter_banner, fmt_int, fmt_money,
                       fmt_pct, guard, insight_box, kpi_row, style_figure)
from ui.data import compute_priorities, get_scope

st.title("Executive Overview")
st.markdown('<div class="dataco-question"><strong>Centrale onderzoeksvraag</strong><br>' + CENTRAL_QUESTION + '</div>', unsafe_allow_html=True)
st.write("")
scope = guard(get_scope())
filter_banner(scope, f"{fmt_int(len(scope.fin))} orderregels · {fmt_int(scope.fin['Order Id'].nunique())} unieke orders")

fin = financial_kpis(scope.fin).iloc[0]
dlv = delivery_kpis(scope.ocs).iloc[0]
dim, dim_one, _ = comparison_dimension(scope.filters)   # per markt, of per categorie als je één markt kiest
single = nothing_to_compare(scope.filters)                # één markt én één categorie: niets te vergelijken
by_dim = financial_kpis(scope.fin, [dim]).sort_values("revenue", ascending=True)
table, *_ = compute_priorities(scope)   # Overview gebruikt enkel de tabel, niet de referenties
enough = table[table["enough_data"]]

kpi_row([
    ("Omzet (netto)", fmt_money(fin["revenue"]), "Som Order Item Total · zie DV1"),
    ("Winst", fmt_money(fin["profit"]), "Som Order Profit Per Order · zie DV1"),
    ("Winstmarge", fmt_pct(fin["margin_pct"]), "Som winst / som omzet (gewogen) · zie DV1"),
    ("Vertraagde orders", fmt_pct(dlv["late_pct"]), f"{fmt_int(dlv['late_orders'])} van {fmt_int(dlv['eligible_orders'])} orders (geannuleerde zendingen uitgesloten) · zie DV2"),
])

left, right = st.columns([1.15, 1.0])
with left:
    with st.container(border=True):
        shown = by_dim.tail(10)   # van klein naar groot gesorteerd: de grootste staan onderaan en dus bovenaan de grafiek
        st.subheader(f"Omzet en winst per {dim_one}" + (" (top 10 op omzet)" if len(shown) < len(by_dim) else ""))
        if single:
            st.info(NOTHING_TO_COMPARE)
        else:
            fig = go.Figure()
            fig.add_bar(name="Omzet", y=shown[dim], x=shown["revenue"], orientation="h", marker_color=C_REVENUE)
            fig.add_bar(name="Winst", y=shown[dim], x=shown["profit"], orientation="h", marker_color=C_PROFIT)
            fig.update_layout(barmode="group", xaxis_title="Bedrag (bronvaluta)")
            st.plotly_chart(style_figure(fig, height=340), width="stretch")
with right:
    with st.container(border=True):
        st.subheader("Top verbeterprioriteiten")
        top = enough[enough["priority"].isin(RISK_CLASSES)].head(3)
        if top.empty:
            st.info("Geen segment met een risico in deze selectie.")
        for i, (_, r) in enumerate(top.iterrows(), start=1):
            st.markdown(f"**{i}. {r['Market']} · {r['Category Name']}** — _{r['priority']}_  \n"
                        f"Omzet {fmt_money(r['revenue'])} · marge {fmt_pct(r['margin_pct'])} · {fmt_pct(r['late_pct'])} vertraagd ({fmt_int(r['eligible_orders'])} orders)  \n"
                        f"{r['reason']}")
        st.page_link("views/dv4.py", label="Bekijk DV4 →", icon="🎯")

bullets = []
if not single and not by_dim.empty:
    best = by_dim.iloc[-1]
    figures = f"({fmt_money(best['revenue'])}); totaalmarge {fmt_pct(fin['margin_pct'])}."
    if dim == "Market":
        bullets.append(f"**{best[dim]}** levert de meeste omzet {figures}")
    else:
        bullets.append(f"In {scope.filters.market} levert **{best[dim]}** de meeste omzet {figures}")
bullets.append(f"{fmt_pct(dlv['late_pct'])} van de in aanmerking komende orders komt te laat; dat is een breed patroon, geen uitschieter in één markt (zie DV2 voor de spreiding).")
n_prio = int((table["priority"] == "Prioriteit").sum())
bullets.append(f"{n_prio} van {len(enough)} segmenten met voldoende data voldoen aan alle drie de prioriteitscriteria (zie DV4).")
bullets.append("Alle uitspraken zijn beschrijvend en zijn onderzoeksprioriteiten, geen bewezen oorzaken of besparingen.")
insight_box("Wat leren we?", bullets)
st.caption("Onderzoeksketen: Bron → Audit → KPI's → DV1–DV4 → Prioriteiten. Bewijs en definities staan per DV en onder *Data & Methode*.")
