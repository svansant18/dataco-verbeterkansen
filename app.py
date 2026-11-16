"""DataCo — one Streamlit research app, six pages, three global filters.

Business logic lives in pipeline.py and analysis/; pages only lay out results.
Never publish an identifiable/raw DataCo CSV. See docs/SPEC.md.
"""
from __future__ import annotations

import streamlit as st

from ui.data import ALL_CATEGORIES, ALL_MARKETS, filter_options, get_result

st.set_page_config(page_title="DataCo · Supply Chain Insights", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """<style>
    .block-container {padding-top: 1.0rem; max-width: 1480px;}
    [data-testid="stSidebar"] {display:none;}
    .dataco-top {
      background: linear-gradient(110deg, #102746, #173c66);
      border-radius: 12px; padding: 16px 21px; color: white;
      margin-bottom: 0.9rem;
    }
    .dataco-top .headline {font-weight: 760;font-size:1.28rem;}
    .dataco-top .subline {color:#d2e8f7; font-size:0.88rem;}
    .dataco-question {border-left: 4px solid #079a9e; padding: 0.7rem 1.0rem;
      background: #ebf8fb; color:#193c53; border-radius:7px;}
    </style>""",
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="dataco-top"><div class="headline">DataCo · Supply Chain Insights</div>'
    '<div class="subline">Van ruwe data naar onderbouwde verbeterprioriteiten · Streamlit onderzoeksproject</div></div>',
    unsafe_allow_html=True,
)

result = get_result()


def reset_filters() -> None:
    st.session_state["global_market"] = ALL_MARKETS
    st.session_state["global_category"] = ALL_CATEGORIES
    if result is not None:
        _, _, d_min, d_max = filter_options(result)
        st.session_state["global_period"] = (d_min, d_max)


# Global filters live in the entrypoint so their state persists when pages switch.
col1, col2, col3, col4 = st.columns([1.0, 1.2, 1.2, 1.1])
if result is None:
    col1.selectbox("Markt", [ALL_MARKETS], key="global_market", disabled=True)
    col2.selectbox("Productcategorie", [ALL_CATEGORIES], key="global_category", disabled=True)
    col3.caption("Periode: beschikbaar zodra een bron aanwezig is")
    col4.caption("**Datasetstatus:** geen bron — geen cijfers")
else:
    markets, categories, d_min, d_max = filter_options(result)
    st.session_state.setdefault("global_period", (d_min, d_max))
    col1.selectbox("Markt", [ALL_MARKETS, *markets], key="global_market")
    col2.selectbox("Productcategorie", [ALL_CATEGORIES, *categories], key="global_category")
    col3.date_input("Orderdatum (periode)", min_value=d_min, max_value=d_max, key="global_period", format="DD/MM/YYYY")
    with col4:
        st.caption("**Datasetstatus:** echte DataCo-data · pipeline technisch gevalideerd · businessgoedkeuring: zie *Data & Methode*")
        st.button("Reset filters", on_click=reset_filters, width="stretch")

# Six logical subpages inside one application, never six Streamlit processes.
pages = [
    st.Page("views/overview.py", title="Overview", icon="🏠", default=True),
    st.Page("views/dv1.py", title="DV1 Omzet & Winst", icon="📊"),
    st.Page("views/dv2.py", title="DV2 Leverbetrouwbaarheid", icon="🚚"),
    st.Page("views/dv3.py", title="DV3 Kortingen & Marges", icon="🏷️"),
    st.Page("views/dv4.py", title="DV4 Prioriteiten", icon="🎯"),
    st.Page("views/methode.py", title="Data & Methode", icon="🧪"),
]
pg = st.navigation(pages, position="top")
pg.run()
