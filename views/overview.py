"""Executive Overview: every number comes from the validated pipeline and the shared filters."""
import plotly.graph_objects as go
import streamlit as st

from analysis.kpis import delivery_kpis, financial_kpis
from ui.common import (C_PROFIT, C_REVENUE, CENTRAL_QUESTION, filter_banner, fmt_int, fmt_money, fmt_pct, guard,
                       insight_box, kpi_row, style_figure)
from ui.data import compute_priorities, get_scope

st.title("Executive Overview")
st.markdown('<div class="dataco-question"><strong>Centrale onderzoeksvraag</strong><br>' + CENTRAL_QUESTION + '</div>', unsafe_allow_html=True)
st.write("")
scope = guard(get_scope())
filter_banner(scope, f"{fmt_int(len(scope.fin))} orderregels · {fmt_int(scope.fin['Order Id'].nunique())} unieke orders")

fin = financial_kpis(scope.fin).iloc[0]
dlv = delivery_kpis(scope.ocs).iloc[0]
by_market = financial_kpis(scope.fin, ["Market"]).sort_values("revenue", ascending=True)
table, refs, fin_kpi, del_kpi = compute_priorities(scope)

kpi_row([
    ("Omzet (netto)", fmt_money(fin["revenue"]), "Som Order Item Total · zie DV1"),
    ("Winst", fmt_money(fin["profit"]), "Som Order Profit Per Order · zie DV1"),
    ("Winstmarge", fmt_pct(fin["margin_pct"]), "Som winst / som omzet (gewogen) · zie DV1"),
    ("Vertraagde orders", fmt_pct(dlv["late_pct"]), f"{fmt_int(dlv['late_orders'])} van {fmt_int(dlv['eligible_orders'])} orders (geannuleerde zendingen uitgesloten) · zie DV2"),
])

left, right = st.columns([1.15, 1.0])
with left:
    with st.container(border=True):
        st.subheader("Omzet en winst per markt")
        fig = go.Figure()
        fig.add_bar(name="Omzet", y=by_market["Market"], x=by_market["revenue"], orientation="h", marker_color=C_REVENUE)
        fig.add_bar(name="Winst", y=by_market["Market"], x=by_market["profit"], orientation="h", marker_color=C_PROFIT)
        fig.update_layout(barmode="group", xaxis_title="Bedrag (bronvaluta)")
        st.plotly_chart(style_figure(fig, height=340), width="stretch")
with right:
    with st.container(border=True):
        st.subheader("Top verbeterprioriteiten")
        enough = table[table["enough_data"]]
        top = enough.head(3)
        if top.empty:
            st.info("Geen segment met voldoende data in deze selectie.")
        for i, (_, r) in enumerate(top.iterrows(), start=1):
            st.markdown(f"**{i}. {r['Market']} · {r['Category Name']}** — _{r['priority']}_  \n"
                        f"Omzet {fmt_money(r['revenue'])} · marge {fmt_pct(r['margin_pct'])} · {fmt_pct(r['late_pct'])} vertraagd ({fmt_int(r['eligible_orders'])} orders)  \n"
                        f"{r['reason']}")
        st.page_link("views/dv4.py", label="Bekijk DV4 →", icon="🎯")

bullets = []
if not by_market.empty:
    best = by_market.iloc[-1]
    bullets.append(f"**{best['Market']}** levert de meeste omzet ({fmt_money(best['revenue'])}); totaalmarge {fmt_pct(fin['margin_pct'])}.")
bullets.append(f"{fmt_pct(dlv['late_pct'])} van de in aanmerking komende orders komt te laat; dat is een breed patroon, geen uitschieter in één markt (zie DV2 voor de spreiding).")
n_prio = int((table["priority"] == "Prioriteit").sum())
bullets.append(f"{n_prio} van {len(enough)} segmenten met voldoende data voldoen aan alle drie de prioriteitscriteria (zie DV4).")
bullets.append("Alle uitspraken zijn beschrijvend en zijn onderzoeksprioriteiten, geen bewezen oorzaken of besparingen.")
insight_box("Wat leren we?", bullets)
st.caption("Onderzoeksketen: Bron → Audit → KPI's → DV1–DV4 → Prioriteiten. Bewijs en definities staan per DV en onder *Data & Methode*.")
