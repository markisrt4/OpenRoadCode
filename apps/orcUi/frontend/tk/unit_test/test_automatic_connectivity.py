# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Connection loss and recovery update feature policy without a Tk display."""
from queue import SimpleQueue
from unittest.mock import Mock, patch

from controllers.connectivity.shell_connectivity_controller import ShellConnectivityController
from controllers.connectivity.online_mode import OnlineModeController


def _app(tmp_path):
    app = ShellConnectivityController.__new__(ShellConnectivityController)
    app.online_mode = OnlineModeController(tmp_path / 'mode.json')
    app._closing = False
    app._network_available = None
    app._network_results = SimpleQueue()
    app._internet_status = None
    app._internet_results = SimpleQueue()
    app._internet_generation = 0
    app._internet_probe_active = True
    app._internet_next_probe = 1
    app._shell = Mock()
    app._dispatcher = Mock()
    app._set_status = Mock()
    app._paint = app._shell.set_online_status
    return app


def test_failed_check_disables_features_and_still_probes_for_recovery(tmp_path):
    app = _app(tmp_path)
    listener = Mock()
    app.online_mode.subscribe(listener)
    app._internet_results.put((0, False))
    with patch('controllers.connectivity.shell_connectivity_controller.Thread') as worker:
        app._poll_internet_status()
        assert not app.online_mode.online
        assert app.online_mode.requested_online
        listener.assert_called_once_with(False)
        app._poll_internet_status()
        worker.assert_called_once()
    app._internet_results.put((0, True))
    app._poll_internet_status()
    assert app.online_mode.online
    assert listener.call_args.args == (True,)
    app._shell.set_online_status.assert_called_with(True, True)


def test_manual_offline_skips_checks_and_ignores_old_results(tmp_path):
    app = _app(tmp_path)
    app._toggle_online_mode()
    app._internet_results.put((0, True))
    with patch('controllers.connectivity.shell_connectivity_controller.Thread') as worker:
        app._poll_internet_status()
        worker.assert_not_called()
    assert not app.online_mode.online
    assert not app.online_mode.requested_online
    assert app._internet_status is None


def test_result_from_before_manual_toggle_cannot_disable_new_online_request(tmp_path):
    app = _app(tmp_path)
    app._toggle_online_mode()
    app._toggle_online_mode()
    app._internet_results.put((0, False))
    with patch('controllers.connectivity.shell_connectivity_controller.Thread'):
        app._poll_internet_status()
    assert app.online_mode.online
    assert app._internet_status is None


def test_local_disconnect_immediately_disables_and_rejects_inflight_success(tmp_path):
    app = _app(tmp_path)
    app._network_results.put(False)
    app._internet_results.put((0, True))
    with patch('controllers.connectivity.shell_connectivity_controller.Thread') as worker:
        app._poll_internet_status()
        worker.assert_not_called()
    assert not app.online_mode.online
    assert app._internet_status is False
    assert app._network_available is False


def test_local_recovery_verifies_internet_without_waiting_for_periodic_timer(tmp_path):
    app = _app(tmp_path)
    app.online_mode.set_reachable(False)
    app._internet_probe_active = False
    app._internet_next_probe = 10
    app._network_available = False
    app._network_results.put(True)
    with patch('controllers.connectivity.shell_connectivity_controller.Thread') as worker:
        app._poll_internet_status()
        worker.assert_called_once()
    assert not app.online_mode.online
    generation = app._internet_generation
    app._internet_results.put((generation, True))
    app._poll_internet_status()
    assert app.online_mode.online


def test_missing_local_monitor_keeps_periodic_checks_available(tmp_path):
    app = _app(tmp_path)
    app._internet_probe_active = False
    app._network_available = False
    app._network_results.put(None)
    with patch('controllers.connectivity.shell_connectivity_controller.Thread') as worker:
        app._poll_internet_status()
        worker.assert_called_once()
    assert app._network_available is None


def test_manual_online_request_does_not_override_known_local_disconnect(tmp_path):
    app = _app(tmp_path)
    app.online_mode.set_online(False)
    app._network_available = False
    app._toggle_online_mode()
    assert app.online_mode.requested_online
    assert not app.online_mode.online
