# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Behavior tests for the rate-limited diagnostics component probe."""

from controllers.automotive.obd2.component_test.obd2_diagnostics_cli import (
    run_scheduled_scan,
)
from protocols.obd2 import Obd2Response


def test_cli_scan_obeys_request_budget_and_uses_semantic_decoder() -> None:
    requests = []
    sleeps = []

    def request(item):
        requests.append((item.mode, item.pid))
        if item.mode == 0x01:
            return (Obd2Response(0x41, 0x01, bytes.fromhex("81000000"), 0x7E8),)
        if item.mode == 0x03:
            return (Obd2Response(0x43, None, bytes.fromhex("0302"), 0x7E8),)
        return ()

    snapshot = run_scheduled_scan(
        request,
        request_rate_hz=5.0,
        sleep=sleeps.append,
    )

    assert requests == [(0x01, 0x01), (0x03, None), (0x07, None), (0x0A, None)]
    assert sleeps == [0.2, 0.2, 0.2]
    assert snapshot.mil_on is True
    assert [item.code for item in snapshot.trouble_codes] == ["P0302"]
