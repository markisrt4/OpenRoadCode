# SPDX-License-Identifier: MIT
"""Guard native composition against eager legacy SDR++ launcher imports."""
import ast
from pathlib import Path


def test_radio_composition_does_not_import_sdrpp_launcher_at_module_load():
    root = Path(__file__).resolve().parents[3]
    source = root / "apps" / "orcUi" / "composition" / "radio.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    eager_imports = [
        node for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and node.module == "apps.launchers.sdrpp_launcher"
    ]
    assert not eager_imports, "Native radio must not eagerly load the SDR++ launcher"


def test_composition_never_imports_legacy_theme_launcher():
    root = Path(__file__).resolve().parents[3]
    source = root / "apps" / "orcUi" / "composition" / "radio.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module == "apps.launchers.sdrpp_launcher"
    ]
    assert not imports
    assert "ORC_SDRFORGE_UI_PREVIEW" not in source.read_text(encoding="utf-8")
