"""Afspraken uit CLAUDE.md die je aan de broncode kan zien. Wat de app doet, staat in test_app_pages.py."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


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
    for f in ("README.md", "CLAUDE.md", "beslissingslogboek.md", "data-exploration.md"):
        assert (ROOT / f).is_file()


def test_no_sidebar_and_no_teacher_or_no_ai_tabs():
    """CLAUDE.md afspraak 8: geen st.sidebar. De pagina Data & Methode heeft geen docent/no-AI-tabs."""
    for path in [ROOT / "app.py", *(ROOT / "views").glob("*.py"), *(ROOT / "ui").glob("*.py")]:
        assert "st.sidebar" not in path.read_text(encoding="utf-8"), path.name
    methode = (ROOT / "views" / "methode.py").read_text(encoding="utf-8")
    assert "Docentcheck" not in methode and "No-AI" not in methode
