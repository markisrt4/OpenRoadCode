# SPDX-License-Identifier: MIT
"""Exercise shell lifecycle without acquiring a real display."""

from threading import Thread
from unittest.mock import Mock

import pytest

from apps.orcUi.frontend.tk.orc_ui_app import OrcUiApp
from frontends.common.ui_callback_queue import UiCallbackQueue


def shell():
    app = OrcUiApp.__new__(OrcUiApp)
    app._closing = False
    app._callback_queue = UiCallbackQueue()
    app._ui_callbacks = set()
    app._root = Mock()
    app._root.after.return_value = "timer"
    app._active_screen = Mock()
    app._power_dialog = Mock()
    app._shell = Mock()
    return app


def test_worker_dispatch_never_calls_tk_and_shutdown_discards_delivery():
    app = shell()
    result = Mock()
    worker = Thread(target=lambda: app.dispatch_ui(result))
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert app._root.mock_calls == []
    result.assert_not_called()
    app.shutdown()
    app.dispatch_ui(result)
    app._callback_queue.dispatch_pending()
    result.assert_not_called()
    assert app.schedule_ui_callback(0, result) is None
    app._root.after.assert_not_called()


def test_shutdown_cancels_timers_and_destroys_root_even_when_screen_hide_fails():
    app = shell()
    screen = app._active_screen
    screen.hide.side_effect = RuntimeError("hide")
    app._ui_callbacks.add("timer")
    with pytest.raises(RuntimeError, match="hide"):
        app.shutdown()
    app._root.after_cancel.assert_called_once_with("timer")
    app._power_dialog.close.assert_called_once()
    app._shell.close.assert_called_once()
    app._root.destroy.assert_called_once()
    app.shutdown()
    screen.hide.assert_called_once()
    app._root.destroy.assert_called_once()


def test_callback_failure_keeps_frontend_pump_scheduled():
    app = shell()

    def fail():
        raise RuntimeError("delivery")

    app.dispatch_ui(fail)
    with pytest.raises(RuntimeError, match="delivery"):
        app._drain_ui_callbacks()
    assert app._root.after.call_args.args[0] == 16


def test_inert_or_foreign_timer_tokens_never_reach_tk():
    app = shell()
    for token in (None, object(), 42, []):
        app.cancel_ui_callback(token)
    app._root.after_cancel.assert_not_called()
