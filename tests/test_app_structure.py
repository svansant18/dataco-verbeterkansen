from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def test_six_streamlit_pages_and_top_navigation():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'position="top"' in app
    assert app.count('st.Page("views/') == 6
    assert 'st.navigation(' in app
    assert not (ROOT / "eda_app.py").exists()


def test_four_questions_have_evidence_panels():
    common = (ROOT / "ui" / "common.py").read_text(encoding="utf-8")
    for q in ("DV1", "DV2", "DV3", "DV4"):
        assert f'"{q}":' in common
    for name in ("dv1", "dv2", "dv3", "dv4"):
        text = (ROOT / "views" / f"{name}.py").read_text(encoding="utf-8")
        assert "evidence_panels(" in text
    components = (ROOT / "ui" / "common.py").read_text(encoding="utf-8")
    assert "Hoe is dit berekend?" in components
    assert "Onderliggende data" in components


def test_pure_pipeline_no_streamlit_dependency():
    tree = ast.parse((ROOT / "pipeline.py").read_text(encoding="utf-8"))
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    modules = []
    for node in imports:
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        else:
            modules.append(node.module or "")
    assert not any(m.startswith("streamlit") for m in modules)


def test_required_documents_exist():
    for f in ("README.md", "CLAUDE.md", "beslissingslogboek.md", "docs/SPEC.md", "docs/KPI_REGISTER.md"):
        assert (ROOT / f).is_file()


def test_no_sidebar_and_no_teacher_or_no_ai_tabs():
    """CLAUDE.md afspraak 8: geen st.sidebar. De pagina Data & Methode heeft geen docent/no-AI-tabs."""
    for path in [ROOT / "app.py", *(ROOT / "views").glob("*.py"), *(ROOT / "ui").glob("*.py")]:
        assert "st.sidebar" not in path.read_text(encoding="utf-8"), path.name
    methode = (ROOT / "views" / "methode.py").read_text(encoding="utf-8")
    assert "Docentcheck" not in methode and "No-AI" not in methode


def test_kpi_register_document_matches_the_code():
    """docs/KPI_REGISTER.md is gemaakt uit analysis/evidence.py (KPI_REGISTER) en mag er niet van afwijken: elk KPI-ID, label en elke formule moet erin staan."""
    from analysis.evidence import KPI_REGISTER

    text = (ROOT / "docs" / "KPI_REGISTER.md").read_text(encoding="utf-8")
    missing = []
    for kid, d in KPI_REGISTER.items():
        for part in (kid, d["label"], d["formula"].replace("|", "\\|")):
            if part not in text:
                missing.append((kid, part[:60]))
    assert not missing, missing
    assert "PENDING AUDIT" not in text and "Som van geldige `Sales`" not in text
