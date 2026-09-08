# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component tests for off-road stylesheet resolution."""

from pathlib import Path

import pytest

from frontends.tk.automotive.offroad_theme import OffroadTheme
from ui.theme import load_theme_bundle


_THEME_ROOT = Path(__file__).resolve().parents[4] / "resources" / "themes"


@pytest.mark.parametrize("filename", ("orc-dark.css", "orc-light.css"))
def test_offroad_theme_resolves_packaged_css(filename: str) -> None:
    bundle = load_theme_bundle(_THEME_ROOT / filename)
    theme = OffroadTheme.from_style_sheet(bundle.style_sheet)
    values = bundle.style_sheet.declarations(".automotive-offroad")

    assert theme.background == values["background"]
    assert theme.panel == values["--panel"]
    assert theme.border == values["--border"]
    assert theme.text == values["color"]
    assert theme.muted == values["--muted"]
    assert theme.primary == values["--heading"]
    assert theme.success == values["--success"]
    assert theme.warning == values["--warning"]
    assert theme.danger == values["--danger"]
    assert theme.sky == values["--sky"]
    assert theme.ground == values["--ground"]
    assert theme.control_background == values["--control-background"]
    assert theme.control_active == values["--control-active"]
    assert theme.control_text == values["--control-text"]


def test_light_offroad_theme_uses_semantic_light_surfaces() -> None:
    bundle = load_theme_bundle(_THEME_ROOT / "orc-light.css")
    theme = OffroadTheme.from_style_sheet(bundle.style_sheet)

    assert theme.background == bundle.ui.background
    assert theme.panel == bundle.ui.surface
    assert theme.text == bundle.ui.text
    assert theme.muted == bundle.ui.text_muted
