"""Root-starter: kies bovenaan een sub-app en laad die.

Een nieuwe sub-app = een map met `app.py` + `main()` en één regel in `SUBAPPS`.
"""

import importlib.util
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# naam in de keuzebalk -> submap
SUBAPPS = {
    "Pijplijn DataCo": "pipeline_dataco",
    "DV1 Omzet & winst": "dv1_omzet_winst",
    "DV2 Leverbetrouwbaarheid": "dv2_leverbetrouwbaarheid",
    "DV3 Kortingen & marges": "dv3_kortingen_marges",
    "DV4 Verbeterprioriteiten": "dv4_verbeterprioriteiten",
}


def laad_subapp(submap: str):
    """Laad `<submap>/app.py` onder een unieke modulenaam en geef de module terug."""
    pad = ROOT / submap / "app.py"
    spec = importlib.util.spec_from_file_location(f"subapp_{submap}", pad)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    st.set_page_config(page_title="DataCo verbeterkansen", layout="wide")
    st.title("DataCo: waar liggen de grootste verbeterkansen?")
    keuze = st.radio("Sub-app", list(SUBAPPS), horizontal=True)
    st.divider()

    # Sub-apps mogen zelf st.set_page_config bevatten; die negeren we hier.
    echte_config = st.set_page_config
    st.set_page_config = lambda *args, **kwargs: None
    try:
        laad_subapp(SUBAPPS[keuze]).main()
    finally:
        st.set_page_config = echte_config


main()
