# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the frontend-neutral theme stylesheet loader."""

from pathlib import Path

import pytest

from ui.theme import load_style_sheet, load_ui_theme


def _write_theme(path: Path, extra_rules: str = "") -> Path:
    path.write_text(
        """
:root {
    --background: #010203;
    --surface: #111213;
    --surface-alt: #212223;
    --border: #313233;
    --text: #f1f2f3;
    --text-muted: #a1a2a3;
    --accent-primary: #123456;
    --accent-success: #234567;
    --accent-warning: #345678;
    --accent-danger: #456789;
    --control-background: var(--surface-alt);
    --control-active: var(--accent-primary);
    --control-text: var(--text);
}

.button {
    background: var(--control-background);
    color: var(--control-text);
}
"""
        + extra_rules,
        encoding="utf-8",
    )
    return path


def test_load_style_sheet_resolves_custom_properties(tmp_path: Path) -> None:
    sheet = load_style_sheet(_write_theme(tmp_path / "theme.css"))

    assert sheet.value(".button", "background") == "#212223"
    assert sheet.value(".button", "color") == "#f1f2f3"


def test_load_ui_theme_builds_semantic_palette(tmp_path: Path) -> None:
    theme = load_ui_theme(_write_theme(tmp_path / "theme.css"))

    assert theme.background == "#010203"
    assert theme.control_background == "#212223"
    assert theme.control_active == "#123456"
    assert theme.control_text == "#f1f2f3"


def test_undefined_custom_property_is_rejected(tmp_path: Path) -> None:
    path = _write_theme(
        tmp_path / "theme.css",
        "\n.bad { background: var(--does-not-exist); }\n",
    )

    with pytest.raises(ValueError, match="Undefined CSS custom property"):
        load_style_sheet(path)


def test_cyclic_custom_properties_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "cycle.css"
    path.write_text(
        """
:root {
    --a: var(--b);
    --b: var(--a);
}

.bad { background: var(--a); }
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Cyclic CSS custom property reference"):
        load_style_sheet(path)
