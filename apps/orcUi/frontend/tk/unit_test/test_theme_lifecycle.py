# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Theme changes must release native hosts before rebuilding their widgets."""
from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from ui.theme import ThemeMode


def application(screen, events):
    app = object.__new__(OrcUiApp)
    app._theme_mode = ThemeMode.DARK
    app._active_screen = screen
    app._active_nav = 'NAV'
    app._root = Mock()
    app._shell = Mock()
    app._power_dialog = Mock()
    app._theme_change_handler = lambda mode: events.append('map theme')
    app._rebuild_shell_theme = lambda: events.append('shell rebuild')
    app.navigate_to = lambda name: events.append(f'show {name}')
    return app


def test_theme_releases_screen_before_map_restart_and_shell_rebuild():
    events = []
    screen = SimpleNamespace(hide=lambda: events.append('hide'))
    app = application(screen, events)
    app._toggle_theme()
    assert events == ['hide', 'map theme', 'shell rebuild', 'show NAV']
    assert app._theme_mode is ThemeMode.LIGHT


def test_screen_with_live_theme_support_is_not_remounted():
    events = []
    screen = SimpleNamespace(hide=Mock(), set_theme_mode=lambda mode: events.append('screen theme'))
    app = application(screen, events)
    app._toggle_theme()
    screen.hide.assert_not_called()
    assert app._active_screen is screen
    assert events == ['map theme', 'shell rebuild', 'screen theme']


def test_theme_without_active_screen_only_updates_shell():
    events = []
    app = application(None, events)
    app._toggle_theme()
    assert events == ['map theme', 'shell rebuild']
