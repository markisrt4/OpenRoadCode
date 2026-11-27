# SPDX-License-Identifier: MIT
"""Exercise the update checks and consent boundary without network access."""

from concurrent.futures import Future
from subprocess import CompletedProcess
from unittest.mock import Mock

import pytest

from controllers.system.software_update import (
    AvailableUpdate,
    CheckoutUpdates,
    SoftwareUpdateController,
)


def test_non_master_skips_fetch(tmp_path):
    checkout = CheckoutUpdates(tmp_path)
    checkout._git = Mock(return_value=CompletedProcess([], 0, stdout="fix/rpi5-cleanup\n"))
    assert checkout.check() is None
    checkout._git.assert_called_once_with("symbolic-ref", "--quiet", "--short", "HEAD", check=False)


def test_changed_checkout_refuses_approved_update(tmp_path):
    checkout = CheckoutUpdates(tmp_path)
    checkout._clean_master_head = Mock(return_value="different-head")
    checkout._git = Mock()
    with pytest.raises(RuntimeError, match="checkout changed"):
        checkout.apply(AvailableUpdate("old", "new"))
    checkout._git.assert_not_called()


def test_restart_runs_only_after_successful_approved_update():
    dispatcher = Mock()
    checkout, offer, restart = Mock(), Mock(), Mock()
    controller = SoftwareUpdateController(
        checkout, dispatcher, online=lambda: True, offer=offer, report_error=Mock(), restart=restart
    )
    result = Future()
    update = AvailableUpdate("old", "123456789abcdef")
    result.set_result(update)

    try:
        controller._show_result(result)
        checkout.apply.assert_not_called()
        restart.assert_not_called()

        revision, accept = offer.call_args.args
        assert revision == "12345678"
        accept()
    finally:
        controller._executor.shutdown(wait=True)
    checkout.apply.assert_called_once_with(update)
    restart.assert_not_called()
    dispatcher.dispatch_ui.call_args.args[0]()
    restart.assert_called_once_with()
    controller.close()
