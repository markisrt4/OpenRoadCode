# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Connection loss and recovery update feature policy without a Tk display."""
from queue import SimpleQueue
from unittest.mock import Mock, patch

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from controllers.connectivity.online_mode import OnlineModeController


def _app(tmp_path):
    app = OrcUiApp.__new__(OrcUiApp)
    app.online_mode = OnlineModeController(tmp_path / 'mode.json')
    app._closing = False
    app._internet_status = None
    app._internet_results = SimpleQueue()
    app._internet_generation = 0
    app._internet_probe_active = True
    app._internet_next_probe = 1
    app._shell = Mock()
    app._root = Mock()
    return app


def test_failed_check_disables_features_and_still_probes_for_recovery(tmp_path):
    app = _app(tmp_path)
    listener = Mock()
    app.online_mode.subscribe(listener)
    app._internet_results.put((0, False))
    with patch('apps.orcUi.frontend.tk.orc_ui_app.Thread') as worker:
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
    with patch('apps.orcUi.frontend.tk.orc_ui_app.Thread') as worker:
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
    with patch('apps.orcUi.frontend.tk.orc_ui_app.Thread'):
        app._poll_internet_status()
    assert app.online_mode.online
    assert app._internet_status is None
