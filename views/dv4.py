"""DV4 — transparent priority rules on top of DV1 + DV2 (no score, no ML, no savings claims)."""
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from analysis.kpis import RISK_CLASSES
from ui.common import (C_LATE, C_MARGIN, C_PROFIT, QUESTIONS, evidence_panels, filter_banner, fmt_int, fmt_money, fmt_pct, guard,
                       kpi_row, page_heading, style_figure)
from ui.data import compute_priorities, get_scope

page_heading("DV4 · Verbeterprioriteiten", QUESTIONS["DV4"])
scope = guard(get_scope())
filter_banner(scope, f"{fmt_int(scope.fin['Order Id'].nunique())} unieke orders in de analysebasis")

table, refs, fin_kpi, del_kpi = compute_priorities(scope)
if table.empty:
    st.info("Geen markt × categorie-segmenten in deze selectie (N/B).")
    st.stop()

enough = table[table["enough_data"]]
counts = table["priority"].value_counts()
kpi_row([
    ("Segmenten (markt × categorie)", fmt_int(len(table)), "Combinaties in de actieve selectie (DV1 ∩ DV2)"),
    (f"Voldoende data (≥ {refs['min_orders']} orders)", fmt_int(len(enough)), "Anders 'Onvoldoende data' — nooit 'laag risico'"),
    ("Segmenten met Prioriteit", fmt_int(counts.get("Prioriteit", 0)), "Hoge omzet + marge onder referentie + vertraging boven referentie"),
    ("Referentie marge · vertraging", f"{fmt_pct(refs['ref_margin_pct'])} · {fmt_pct(refs['ref_late_pct'])}", "Gewogen totalen van alle markten en categorieën in de gekozen periode (DV1 resp. DV2)"),
])
if scope.filters.market or scope.filters.category:
    st.caption("Een filter op markt of categorie zoomt in: de referenties en de klassen blijven die van het hele bedrijf in de gekozen periode.")

STYLE = {"Prioriteit": ("#DC2626", "diamond"), "Optimaliseren": (C_LATE, "square"), "Monitoren": (C_MARGIN, "triangle-up"), "Sterk": (C_PROFIT, "circle")}
left, right = st.columns([1.15, 0.95])
with left:
    with st.container(border=True):
        st.subheader("Prioriteitenmatrix")
        fig = go.Figure()
        sizeref = 2.0 * max(enough["revenue"].max(), 1) / (45.0 ** 2) if len(enough) else 1
        for cls, (color, symbol) in STYLE.items():
            sub = enough[enough["priority"] == cls]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["late_pct"], y=sub["margin_pct"], mode="markers", name=cls,
                marker=dict(size=sub["revenue"], sizemode="area", sizeref=sizeref, sizemin=5, color=color, symbol=symbol, opacity=0.75, line=dict(width=1, color="white")),
                customdata=np.stack([sub["Market"], sub["Category Name"], sub["revenue"], sub["profit"], sub["eligible_orders"], sub["reason"]], axis=-1),
                hovertemplate=(
                    "<b>%{customdata[0]} · %{customdata[1]}</b><br>"
                    "% vertraagd: %{x:.1f}% · marge: %{y:.1f}%<br>"
                    "Omzet: %{customdata[2]:,.0f} · winst: %{customdata[3]:,.0f}<br>"
                    "Orders: %{customdata[4]:,}<br>%{customdata[5]}<extra></extra>"
                ),
            ))
        if refs["ref_late_pct"] is not None:
            fig.add_vline(x=refs["ref_late_pct"], line_dash="dot", line_color="gray", annotation_text="ref. vertraging")
        if refs["ref_margin_pct"] is not None:
            fig.add_hline(y=refs["ref_margin_pct"], line_dash="dot", line_color="gray", annotation_text="ref. marge")
        fig.update_layout(xaxis_title="% vertraagde orders", yaxis_title="Gewogen winstmarge (%)")
        st.plotly_chart(style_figure(fig, height=430), width="stretch")
        st.caption(f"Bubbelgrootte = omzet. Vorm én kleur geven de klasse aan. {len(table) - len(enough)} segmenten met onvoldoende data zijn niet getekend.")
with right:
    with st.container(border=True):
        st.subheader("Top 5 verbeterprioriteiten")
        top = enough[enough["priority"].isin(RISK_CLASSES)].head(5).copy()
        if top.empty:
            st.info("Geen segment met een risico in deze selectie.")
        else:
            view = top[["priority", "Market", "Category Name", "revenue", "margin_pct", "late_pct", "eligible_orders", "reason"]].rename(columns={
                "priority": "Klasse", "Market": "Markt", "Category Name": "Categorie", "revenue": "Omzet", "margin_pct": "Marge %",
                "late_pct": "% vertraagd", "eligible_orders": "Orders", "reason": "Reden"})
            view.insert(0, "#", range(1, len(view) + 1))
            st.dataframe(view.round(1), width="stretch", hide_index=True)
        st.caption("Alleen segmenten met een risico (Prioriteit, Optimaliseren, Monitoren), gesorteerd op klasse, daarna omzet dalend, markt, categorie.")

# --- conclusion generated from the table ---
with st.container(border=True):
    st.subheader("Conclusie & aanbevelingen")
    prio = enough[enough["priority"] == "Prioriteit"]
    if prio.empty:
        lead = "Geen enkel segment voldoet in deze selectie aan alle drie de prioriteitscriteria tegelijk."
    else:
        names = "; ".join(
            f"**{r['Market']} · {r['Category Name']}** (omzet {fmt_money(r['revenue'])}, "
            f"marge {fmt_pct(r['margin_pct'])}, {fmt_pct(r['late_pct'])} vertraagd)"
            for _, r in prio.head(3).iterrows()
        )
        lead = f"{len(prio)} segment(en) voldoen aan alle drie de criteria; de grootste naar omzet: {names}."
    st.markdown(
        f"{lead} Deze selectie bevat {len(table)} segmenten, waarvan {len(enough)} met voldoende data. "
        f"Referenties: marge {fmt_pct(refs['ref_margin_pct'])}, vertraging {fmt_pct(refs['ref_late_pct'])}. "
        "Dit zijn **onderzoeksprioriteiten (hypothesen)**, geen bewezen oorzaken en geen eurobesparing."
    )
    st.markdown(
        "**Voorgestelde acties:** 1) onderzoek de oorzaken van vertraging in de prioriteitssegmenten; "
        "2) verifieer korting en marge in die segmenten (zie DV3); "
        "3) monitor 'Optimaliseren'- en 'Monitoren'-segmenten."
    )

# --- trace back: DV4 -> DV1/DV2 -> pipeline ---
with st.container(border=True):
    st.subheader("Terugvolgen: van prioriteit naar bronberekening")
    if enough.empty:
        st.info("Geen segmenten met voldoende data om terug te volgen.")
    else:
        labels = [f"{r['Market']} · {r['Category Name']} ({r['priority']})" for _, r in enough.iterrows()]
        pick = st.selectbox("Kies een segment", labels, index=0)
        row = enough.iloc[labels.index(pick)]
        a, b, c = st.columns(3)
        a.markdown(
            f"**DV1 (omzet/winst)**  \nOmzet {fmt_money(row['revenue'])}  \nWinst {fmt_money(row['profit'])}  \n"
            f"Marge = {fmt_money(row['profit'])} / {fmt_money(row['revenue'])} = **{fmt_pct(row['margin_pct'])}**"
        )
        b.markdown(f"**DV2 (levering)**  \n{fmt_int(row['late_orders'])} vertraagd van {fmt_int(row['eligible_orders'])} orders  \n= **{fmt_pct(row['late_pct'])}**")
        c.markdown(
            f"**Regel toegepast**  \n≥ {refs['min_orders']} orders: {'ja' if row['enough_data'] else 'nee'}  \n"
            f"Omzet ≥ mediaan ({fmt_money(refs['median_revenue_qualifying'])}): {'ja' if row['high_volume'] else 'nee'}  \n"
            f"Marge < {fmt_pct(refs['ref_margin_pct'])}: {'ja' if row['low_margin'] else 'nee'}  \n"
            f"Vertraging > {fmt_pct(refs['ref_late_pct'])}: {'ja' if row['high_late'] else 'nee'}"
        )
        st.caption(
            "Volgende stap terug: pipeline-functies `step_validate` → `step_clean` → `step_scope` → "
            "`build_order_category_shipping` (zie Data & Methode) → ruwe CSV (SHA-256 in de verantwoording)."
        )

detail = table.rename(columns={
    "Market": "Markt", "Category Name": "Categorie", "revenue": "Omzet", "profit": "Winst", "margin_pct": "Marge %", "late_pct": "% vertraagd",
    "eligible_orders": "Orders in aanmerking", "late_orders": "Vertraagd", "lines": "Orderregels", "priority": "Klasse", "reason": "Reden",
    "enough_data": "Voldoende data", "high_volume": "Hoge omzet", "low_margin": "Marge < ref.", "high_late": "Vertraging > ref."})[
    ["Klasse", "Markt", "Categorie", "Omzet", "Winst", "Marge %", "% vertraagd", "Orders in aanmerking", "Vertraagd",
     "Voldoende data", "Hoge omzet", "Marge < ref.", "Vertraging > ref.", "Reden"]].round(2)
evidence_panels(
    {"K-PRIO": dict(numerator=len(prio), denominator=len(enough), result=len(prio), input_rows=len(fin_kpi), analysis_rows=len(enough)),
     "K-MARGIN": dict(numerator=fin_kpi["profit"].sum(), denominator=fin_kpi["revenue"].sum(), result=refs["ref_margin_pct"],
                      input_rows=len(fin_kpi), analysis_rows=len(fin_kpi)),
     "K-LATEPCT": dict(numerator=del_kpi["late_orders"].sum(), denominator=del_kpi["eligible_orders"].sum(),
                       result=refs["ref_late_pct"], input_rows=len(del_kpi), analysis_rows=len(del_kpi))},
    scope, detail, file_stem="dv4_prioriteiten",
    notes=(f"Beslisregels (D-010): minimaal {refs['min_orders']} in aanmerking komende orders; "
           f"Prioriteit = omzet ≥ mediaan van kwalificerende segmenten ({fmt_money(refs['median_revenue_qualifying'])}) "
           f"EN marge < {fmt_pct(refs['ref_margin_pct'])} EN vertraging > {fmt_pct(refs['ref_late_pct'])}.",
           "Optimaliseren = vertraging boven referentie · Monitoren = marge onder referentie · Sterk = geen risicocombinatie · Onvoldoende data = < 30 orders of onbekende marge.",
           "Rijen in deze verantwoording zijn segmenten (markt × categorie), niet orderregels. DV4 gebruikt uitsluitend de DV1- en DV2-aggregaties van dezelfde filters.",
           "Tie-break: klasse, omzet dalend, markt, categorie (alfabetisch)."),
)
