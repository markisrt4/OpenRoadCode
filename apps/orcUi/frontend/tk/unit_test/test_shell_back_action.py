# SPDX-License-Identifier: MIT
"""Back actions follow the active screen rather than stale destinations."""

from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from apps.orcUi.frontend.tk.shell_view import OrcUiShellView


def test_shell_back_control_runs_replacement_and_hides_when_cleared():
    shell = OrcUiShellView.__new__(OrcUiShellView)
    shell._back_button = Mock()
    first, second = Mock(), Mock()
    shell.set_back_action(first)
    shell.set_back_action(second)
    shell._request_back()
    first.assert_not_called()
    second.assert_called_once()
    shell.set_back_action(None)
    shell._request_back()
    second.assert_called_once()
    shell._back_button.grid_remove.assert_called_once()


def test_switching_screens_clears_old_action_before_new_screen_binds():
    app = OrcUiApp.__new__(OrcUiApp)
    app._shell = Mock()
    previous, current = Mock(), Mock()
    app._active_screen = previous
    events = []
    previous.hide.side_effect = lambda: events.append("hide")
    app._shell.set_back_action.side_effect = lambda action: events.append(action)
    app.activate_screen(current)
    action = Mock()
    app.set_screen_back_action(action)
    assert events == ["hide", None, action]
    app.activate_screen(current)
    assert events == ["hide", None, action]


def test_placeholder_navigation_clears_previous_back_action():
    app = OrcUiApp.__new__(OrcUiApp)
    app._shell = Mock()
    app._active_nav = "MEDIA"
    app._screen_registry = {}
    app._active_screen = Mock()
    app._root = Mock()
    with patch.object(app, "_show_placeholder"):
        app.navigate_to("HOME")
    assert app._shell.set_back_action.call_args.args == (None,)
