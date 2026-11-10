# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Waze is selected through the shared Views control with semantic requests."""
from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from apps.orcUi.frontend.tk.navigation_panel_layout import build_navigation_panel


def test_waze_is_exposed_through_the_shared_views_selector():
    panel = Mock()
    panel._map_platform = None
    with patch('apps.orcUi.frontend.tk.navigation_panel_layout.tk') as tk, \
            patch('frontends.tk.navigation_experience_controls.NavigationExperienceControls') as controls:
        build_navigation_panel(panel)
    assert controls.call_args.kwargs['handler'] is panel._experience_handler
    assert panel._experience_controls is controls.return_value
    panel._build_radar_controls.assert_called_once_with(controls.return_value.overlay_frame)
    assert not any(call.kwargs.get('text') == 'WAZE' for call in tk.Button.call_args_list)


def test_selecting_waze_in_views_emits_the_semantic_request():
    from frontends.tk.navigation_experience_controls import NavigationExperienceControls
    from ui.navigation.navigation_experience_if import NavigationExperience
    controls = Mock()
    NavigationExperienceControls._select(controls, NavigationExperience.WAZE)
    controls.close_drawer.assert_called_once_with()
    controls._handler.request_experience.assert_called_once_with(NavigationExperience.WAZE)


def test_no_waze_control_when_configuration_disabled():
    panel = Mock()
    panel._map_platform = None
    panel._waze_handler = None
    panel._experience_handler = None
    with patch('apps.orcUi.frontend.tk.navigation_panel_layout.tk') as tk:
        build_navigation_panel(panel)
    assert not any(call.kwargs.get('text') == 'WAZE' for call in tk.Button.call_args_list)


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
