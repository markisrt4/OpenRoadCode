# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Screen subscriptions must not retain destroyed diagnostic widgets."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
from apps.orcUi.frontend.tk.vehicle_screen import VehicleScreen

def test_remount_and_hide_unsubscribe_before_replacing_widgets():
    host = Mock()
    handler = Mock()
    remove_first, remove_second = Mock(), Mock()
    handler.observe.side_effect = [remove_first, remove_second]
    first, second = Mock(), Mock()
    screen = VehicleScreen(
        host, theme_bundle=lambda: None, presentation=SimpleNamespace(
            vehicle=None, trip=None, engine_analysis=None),
        telemetry_profile_request=None, vehicle_configuration=lambda: None,
        on_back=lambda: None, diagnostics_handler=handler,
    )
    with patch('apps.orcUi.frontend.tk.vehicle_screen.build_vehicle_screen', side_effect=[first, second]):
        screen.show()
        handler.observe.assert_called_with(first.update_diagnostics)
        screen.show()
        remove_first.assert_called_once()
        handler.observe.assert_called_with(second.update_diagnostics)
        screen.hide()
        remove_second.assert_called_once()
        screen.close()
        remove_second.assert_called_once()
