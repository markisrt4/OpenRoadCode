# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Waze is a right-aligned Navigation action with semantic requests."""
from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from apps.orcUi.frontend.tk.navigation_panel_layout import build_navigation_panel


def test_waze_button_is_on_right_of_top_bar_and_emits_request():
    panel = Mock()
    panel._map_platform = None
    buttons = []
    def button(*args, **kwargs):
        widget = Mock()
        buttons.append((widget, args, kwargs))
        return widget
    with patch('apps.orcUi.frontend.tk.navigation_panel_layout.tk') as tk:
        tk.Button.side_effect = button
        build_navigation_panel(panel)
        widget, args, kwargs = next(item for item in buttons if item[2].get('text') == 'Waze')
        widget.pack.assert_called_once_with(side=tk.RIGHT, padx=4, pady=3)
        assert args[0] is panel._build_radar_controls.call_args.args[0]
        kwargs['command']()
    panel._waze_handler.request_open_waze.assert_called_once()


def test_no_waze_control_when_configuration_disabled():
    panel = Mock()
    panel._map_platform = None
    panel._waze_handler = None
    with patch('apps.orcUi.frontend.tk.navigation_panel_layout.tk') as tk:
        build_navigation_panel(panel)
    assert not any(call.kwargs.get('text') == 'Waze' for call in tk.Button.call_args_list)


def test_online_change_updates_waze_button():
    panel = object.__new__(NavigationPanel)
    panel._waze_button = Mock()
    panel._online_mode = Mock(online=False)
    panel._earth_button = None
    panel._poi_action_buttons = []
    panel._refresh_poi_action_buttons()
    panel._waze_button.configure.assert_called_with(state='disabled')
    panel._online_mode.online = True
    panel._refresh_poi_action_buttons()
    panel._waze_button.configure.assert_called_with(state='normal')
