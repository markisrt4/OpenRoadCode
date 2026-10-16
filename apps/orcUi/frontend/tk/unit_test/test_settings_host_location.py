# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from unittest.mock import Mock, patch

from common.units import UnitSystem
from apps.orcUi.frontend.tk.settings_screen import SettingsScreen
from apps.orcUi.frontend.tk.settings_panel import SettingsPanel
from ui.navigation.host_location_ui_if import HostLocationState


def test_settings_binds_host_requests_and_drops_hidden_panel_updates():
    host, handler, panel = Mock(), Mock(), Mock()
    screen = SettingsScreen(host, theme_bundle=Mock(), telemetry_profile_request=None,
                            vehicle_configuration=Mock(), on_vehicle_configuration_changed=Mock(),
                            unit_system=lambda: UnitSystem.IMPERIAL, on_unit_system_changed=Mock(), on_back=Mock())
    screen.set_host_location_request_handler(handler)
    state = HostLocationState('Ready')
    screen.set_host_location_state(state)
    with patch('apps.orcUi.frontend.tk.settings_screen.build_settings_screen', return_value=panel) as build:
        screen.show()
    handler.show.assert_called_once()
    assert build.call_args.kwargs['host_location_handler'] is handler
    assert build.call_args.kwargs['host_location_state'] == state
    pending = HostLocationState('Checking', busy=True)
    screen.set_host_location_state(pending)
    panel.set_host_location_state.assert_called_once_with(pending)
    screen.hide()
    handler.hide.assert_called_once()
    panel.reset_mock()
    screen.set_host_location_state(HostLocationState('Late'))
    panel.set_host_location_state.assert_not_called()


def test_share_button_emits_only_the_semantic_request():
    panel = object.__new__(SettingsPanel)
    panel._location_handler = Mock()
    panel._share_host_location()
    panel._location_handler.share_host_location.assert_called_once()


def test_repeated_resize_events_do_not_reconfigure_the_same_geometry():
    label = Mock()
    label.cget.return_value = 200
    SettingsPanel._update_location_wrap(label, 200)
    label.configure.assert_not_called()
    SettingsPanel._update_location_wrap(label, 240)
    label.configure.assert_called_once_with(wraplength=240)
    label.cget.return_value = 240
    SettingsPanel._update_location_wrap(label, 240)
    label.configure.assert_called_once()
