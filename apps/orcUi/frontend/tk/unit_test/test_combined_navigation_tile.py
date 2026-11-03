# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import os
from types import SimpleNamespace
from unittest.mock import Mock
import tkinter as tk
import pytest

from apps.orcUi.frontend.tk.side_nav import OrcUiSideNav, _navigation_slots
from apps.orcUi.theme_runtime import theme_bundle
from ui.theme import ThemeMode


def test_nav_and_waze_are_one_slot_without_changing_the_other_destinations():
    assert _navigation_slots(['HOME', 'NAVIGATION', 'WAZE', 'RADIO']) == [
        ('HOME',), ('NAVIGATION', 'WAZE'), ('RADIO',)]
    assert _navigation_slots(['HOME', 'NAVIGATION', 'RADIO']) == [('HOME',), ('NAVIGATION',), ('RADIO',)]


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='real rail geometry needs X11')
def test_combined_tile_has_two_independent_half_height_targets_and_active_states():
    root = tk.Tk()
    root.geometry('110x700')
    navigate = Mock()
    items = ['HOME', 'NAVIGATION', 'WAZE', 'RADIO', 'VEHICLE', 'WEATHER', 'VISION', 'MEDIA', 'GAMES']
    theme = theme_bundle(ThemeMode.DARK)
    rail = OrcUiSideNav(root, theme=theme, items=items, active='WAZE', on_navigate=navigate)
    rail.pack(fill='both', expand=True)
    try:
        root.update()
        nav, waze, radio = (rail._tiles[key] for key in ('NAVIGATION', 'WAZE', 'RADIO'))
        assert nav.master is waze.master
        assert abs(nav.winfo_height() - waze.winfo_height()) <= 1
        assert abs(nav.master.winfo_height() - radio.winfo_height()) <= 2
        assert nav.winfo_rooty() < waze.winfo_rooty()
        assert waze._selected and not nav._selected
        nav._on_click(SimpleNamespace(y_root=0))
        navigate.assert_called_with('NAVIGATION')
        waze._on_click(SimpleNamespace(y_root=0))
        navigate.assert_called_with('WAZE')
        rail.set_active(active='NAVIGATION', theme=theme)
        assert nav._selected and not waze._selected
        assert len(rail._slots) == 8
        assert str(rail._down_button.cget('state')) == 'disabled'
        rail.rebuild(theme=theme_bundle(ThemeMode.LIGHT), items=items, active='WAZE')
        root.update()
        assert rail._tiles['WAZE']._selected
    finally:
        root.destroy()
