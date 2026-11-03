# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""One rail destination restores the selected map through injected requests."""
import os
from unittest.mock import Mock
import tkinter as tk
import pytest

from apps.orcUi.frontend.tk.side_nav import OrcUiSideNav
from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.theme_runtime import theme_bundle
from controllers.navigation.navigation_view_controller import NavigationViewController
from ui.theme import ThemeMode


def test_nav_rail_restores_last_selected_view_without_intercepting_explicit_map_requests():
    map_view, waze = Mock(), Mock()
    selection = NavigationViewController(open_map=map_view, open_waze=waze)
    app = OrcUiApp.__new__(OrcUiApp)
    app.navigate_to = Mock()
    app.register_navigation_action('NAVIGATION', selection.request_resume_navigation)
    app._navigate_from_sidebar('NAVIGATION')
    map_view.assert_called_once_with()
    selection.remember_waze()
    app._navigate_from_sidebar('NAVIGATION')
    waze.assert_called_once_with()
    app._navigate_from_sidebar('RADIO')
    app.navigate_to.assert_called_once_with('RADIO')
    selection.remember_map()
    app._navigate_from_sidebar('NAVIGATION')
    assert map_view.call_count == 2


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='real rail geometry needs X11')
def test_rail_has_one_full_navigation_tile_and_one_icon():
    root = tk.Tk()
    root.geometry('110x700')
    items = ['HOME', 'NAVIGATION', 'RADIO', 'VEHICLE', 'WEATHER', 'VISION', 'MEDIA', 'GAMES']
    rail = OrcUiSideNav(root, theme=theme_bundle(ThemeMode.DARK), items=items,
                        active='NAVIGATION', on_navigate=Mock())
    rail.pack(fill='both', expand=True)
    try:
        root.update()
        assert 'WAZE' not in rail._tiles
        nav = rail._tiles['NAVIGATION']
        assert len(nav.find_all()) > 0
        assert sum(nav.type(item) == 'polygon' for item in nav.find_all()) == 1
        assert nav._selected
        assert abs(nav.winfo_height() - rail._tiles['RADIO'].winfo_height()) <= 1
    finally:
        root.destroy()
