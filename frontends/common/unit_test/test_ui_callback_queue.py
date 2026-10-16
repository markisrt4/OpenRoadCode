# SPDX-License-Identifier: MIT
"""Verify worker delivery and late completion handling without a display."""

from threading import Thread, get_ident

import pytest

from frontends.common.ui_callback_queue import UiCallbackQueue


def test_worker_submission_runs_only_when_frontend_drains():
    queue = UiCallbackQueue()
    delivered = []
    worker = Thread(target=lambda: queue.dispatch_ui(lambda: delivered.append(get_ident())))
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert delivered == []
    queue.dispatch_pending()
    assert delivered == [get_ident()]


def test_close_discards_pending_and_late_worker_results():
    queue = UiCallbackQueue()
    delivered = []
    queue.dispatch_ui(lambda: delivered.append("pending"))
    queue.close()
    worker = Thread(target=lambda: queue.dispatch_ui(lambda: delivered.append("late")))
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    queue.close()
    queue.dispatch_pending()
    assert delivered == []


def test_reentrant_shutdown_stops_remaining_callbacks():
    queue = UiCallbackQueue()
    delivered = []
    queue.dispatch_ui(queue.close)
    queue.dispatch_ui(lambda: delivered.append("late"))
    queue.dispatch_pending()
    assert delivered == []


def test_bounded_batch_and_callback_failure_leave_remaining_work_available():
    queue = UiCallbackQueue()
    delivered = []
    queue.dispatch_ui(lambda: delivered.append(1))
    queue.dispatch_ui(lambda: delivered.append(2))
    queue.dispatch_pending(limit=1)
    assert delivered == [1]
    queue.dispatch_pending()
    assert delivered == [1, 2]

    def fail():
        raise RuntimeError("callback")

    queue.dispatch_ui(fail)
    queue.dispatch_ui(lambda: delivered.append(3))
    with pytest.raises(RuntimeError, match="callback"):
        queue.dispatch_pending()
    queue.dispatch_pending()
    assert delivered == [1, 2, 3]
