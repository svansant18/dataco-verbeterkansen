"""Data & Methode: the evidence centre. Everything here is read from the real pipeline run."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analysis.evidence import KPI_REGISTER
from ui.common import fmt_int, guard, style_figure
from ui.data import get_scope, processed_for, processed_provenance

ROOT = Path(__file__).resolve().parents[1]
st.title("Data & Methode")
st.caption("Van ruwe DataCo-data tot controleerbare KPI's — pipeline, kwaliteit, definities en beslissingen")
scope = guard(get_scope())
result = scope.result

pipeline_tab, audit_tab, kpi_tab, decisions_tab = st.tabs(
    ["Rijentrechter & pipeline", "Data-audit", "KPI-definities", "Aannames & keuzes"]
)

STEP_INFO = {
    "Bron ingelezen": ("read_analysis_source", "Leest alleen de 13 analysekolommen uit de CSV (latin1). Persoonsgegevens worden niet ingelezen.", "Geen rij kan hier wegvallen."),
    "Validatie": ("step_validate", "Controleert sleutels, verplichte waarden, parsebare orderdatum en unieke Order Item Id.", "Redenen zijn exclusief: een rij krijgt maximaal één reden."),
    "Opschonen": ("step_clean", "Trimt tekst (4 categorienamen hadden een spatie achteraan; 0 categorieën samengevoegd), zet types, bepaalt is_late / delivery_eligible. Onbekende leverstatus stopt de run (geen gok).", "Alleen hertypering; rijen blijven behouden."),
    "Analysebasis (omzet/winst)": ("step_scope", "Laat orders met status CANCELED of SUSPECTED_FRAUD buiten omzet en winst (D-007).", "Dit is de enige echte rij-uitval."),
}

with pipeline_tab:
    st.subheader("Rijentrechter (volledige bron, onafhankelijk van de filters)")
    stages = result.stage_audit
    start, final = stages[0].rows_in, stages[-1].rows_out
    c1, c2, c3 = st.columns(3)
    c1.metric("Bronrijen (orderregels)", fmt_int(start))
    c2.metric("Analysebasis", fmt_int(final))
    c3.metric("Echt uitgesloten", fmt_int(start - final), help="Som van de exclusieve uitsluitingsredenen")
    funnel = go.Figure(go.Funnel(y=[s.name for s in stages], x=[s.rows_out for s in stages], textinfo="value"))
    st.plotly_chart(style_figure(funnel, height=260), width="stretch")
    st.info(f"**Actieve analysepopulatie (na jouw filters):** {fmt_int(len(scope.fin))} orderregels. Filters wijzigen de bronrijentrechter hierboven niet.")
    for i, s in enumerate(stages, start=1):
        func, purpose, note = STEP_INFO[s.name]
        with st.expander(f"Stap {i} · {s.name} — {fmt_int(s.rows_in)} → {fmt_int(s.rows_out)}", expanded=(i == len(stages))):
            st.markdown(f"**Functie:** `pipeline.{func}` · **Doel:** {purpose}")
            st.markdown(f"**Input:** {fmt_int(s.rows_in)} · **Output:** {fmt_int(s.rows_out)} · **Uitgesloten:** {fmt_int(s.rows_excluded)} — {note}")
            if s.primary_exclusion_reasons:
                reasons = pd.DataFrame({"Reden (exclusief)": list(s.primary_exclusion_reasons), "Rijen": list(s.primary_exclusion_reasons.values())})
                st.dataframe(reasons, hide_index=True, width="stretch")
                st.caption(f"Controle: {' + '.join(fmt_int(v) for v in s.primary_exclusion_reasons.values())} = {fmt_int(s.rows_excluded)} ✔")
            else:
                st.caption("Geen uitsluitingsredenen: 0 rijen verwijderd in deze stap.")
            if i == len(stages):
                st.markdown("**Veilige voorbeeldrijen na deze stap** (geen persoonsgegevens):")
                st.dataframe(result.financial_rows[["Order Id", "Order Item Id", "Market", "Category Name", "order_date", "Order Item Total", "Order Profit Per Order", "Delivery Status"]].head(5),
                             hide_index=True, width="stretch")

    st.subheader("Grainconversies (aggregatie, géén rijuitval)")
    g = result.grain_audit
    gc1, gc2, gc3 = st.columns(3)
    gc1.metric("Orderregels → unieke orders", f"{fmt_int(g['order_lines'])} → {fmt_int(g['unique_orders'])}")
    gc2.metric("Order × categorie-relaties", fmt_int(g["order_category_pairs"]), help="Een order met meerdere categorieën telt in elke categorie één keer.")
    gc3.metric("Markt × categorie-segmenten", fmt_int(g["market_category_combinations_financial"]))
    st.caption("Deze omzettingen verminderen het aantal rijen door groeperen. Ze staan bewust niet in de rijentrechter.")

    st.subheader("Herkomst en processed-versies")
    m = result.source_manifest
    st.markdown(f"**Bron:** `{m['source_file']}` · SHA-256 `{m['source_sha256']}` · ongewijzigd na de run: **{'ja' if m['raw_hash_unchanged_after_run'] else 'NEE'}**")
    st.caption(
        "Dataset: *DataCo SMART SUPPLY CHAIN FOR BIG DATA ANALYSIS* van Fabian Constante, Fernando Silva en António Pereira, "
        "Mendeley Data, doi:10.17632/8gx2fvg2k6, gedownload via Kaggle (shashwatwork). Licentie volgens Mendeley: CC BY 4.0 "
        "(https://creativecommons.org/licenses/by/4.0/); volgens Kaggle: CC0 1.0. We vermelden de bron in elk geval. "
        "Bewerkt: deze app gebruikt 13 van de 53 kolommen en laat geannuleerde en "
        "vermoedelijk frauduleuze orders buiten de omzet en winst."
    )
    prov = processed_provenance()
    if prov:
        st.dataframe(pd.DataFrame([{k: p[k] for k in ("processed_file", "processed_sha256", "input_rows", "output_rows", "created_at_utc", "status")} for p in prov]),
                     hide_index=True, width="stretch")
        st.caption("Gekoppeld aan deze brondata: " + ("ja" if processed_for(result) else "NEE — hash verschilt"))
    else:
        st.warning("Nog geen processed-versie opgeslagen. Genereer ze met `python -c \"import pipeline; pipeline.build_processed()\"`.")

with audit_tab:
    st.subheader("Bron-audit — feiten, geen goedkeuring")
    g = result.grain_audit
    st.dataframe(pd.DataFrame({"Meting": list(g), "Waarde": [str(v) for v in g.values()]}), hide_index=True, width="stretch")
    st.subheader("Kwaliteitscontroles")
    q = result.quality_report
    st.dataframe(pd.DataFrame({"Controle": list(q), "Resultaat": [str(v) for v in q.values()]}), hide_index=True, width="stretch")
    st.subheader("Ingelezen kolommen")
    fields = pd.DataFrame({"Kolom": result.financial_rows.columns, "Type": [str(t) for t in result.financial_rows.dtypes], "Lege waarden": result.financial_rows.isna().sum().values})
    st.dataframe(fields, hide_index=True, width="stretch")
    st.warning("De bron bevat persoonsgegevens (o.a. klant-e-mail, wachtwoord, naam, adres). Die kolommen worden **nooit ingelezen** en komen nergens in de app, exports of Git.")

with kpi_tab:
    st.subheader("KPI-register (één bron voor de uitleg op elke DV-pagina)")
    reg = pd.DataFrame([{
        "KPI-ID": k, "Label": d["label"], "DV": d["question_id"], "Formule": d["formula"], "Teller": d["numerator"], "Noemer": d["denominator"],
        "Eenheid": d["unit"], "Grain": d["grain"], "Bronkolommen": ", ".join(d["source_columns"]), "Ontbrekend/nul": d["missing_rule"],
        "Beslissing": d["decision_id"], "Tests": "; ".join(t.split("::")[-1] for t in d["test_ids"]), "Beperking": d["caveat"],
    } for k, d in KPI_REGISTER.items()])
    st.dataframe(reg, hide_index=True, width="stretch")
    pick = st.selectbox("Bekijk één KPI", list(KPI_REGISTER))
    st.json(KPI_REGISTER[pick], expanded=True)
    st.subheader("Didactisch rekenvoorbeeld (fictieve cijfers, geen DataCo-uitkomst)")
    example = pd.DataFrame({"Orderregel": ["a", "b"], "Omzet": [100.0, 900.0], "Winst": [50.0, 90.0], "Regelmarge %": [50.0, 10.0]})
    st.dataframe(example, hide_index=True)
    st.markdown("Gemiddelde van marges = (50 + 10) / 2 = **30%** ✘ · Gewogen marge = (50 + 90) / (100 + 900) = **14%** ✔")

with decisions_tab:
    st.subheader("Aannames & beslissingen")
    st.markdown((ROOT / "beslissingslogboek.md").read_text(encoding="utf-8"))
