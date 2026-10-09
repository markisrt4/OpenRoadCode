# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for generic OBD-II diagnostic scanning."""

import unittest
import threading
import time

from controllers.automotive.obd2.obd2_diagnostics import (
    Obd2DiagnosticStatus,
    Obd2DiagnosticsScanSession,
    Obd2DiagnosticsScanner,
)
from controllers.automotive.obd2.obd2_manager import Obd2Manager
from protocols.obd2 import Obd2AdapterIf, Obd2Request, Obd2Response


class _Adapter(Obd2AdapterIf):
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    @property
    def is_connected(self) -> bool:
        return True

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def request(self, request: Obd2Request) -> tuple[Obd2Response, ...]:
        self.requests.append((request.mode, request.pid))
        return self.responses.get((request.mode, request.pid), ())


class Obd2DiagnosticsScannerTest(unittest.TestCase):
    def test_incremental_session_exposes_one_request_per_step(self) -> None:
        session = Obd2DiagnosticsScanSession()
        requests = []
        while (request := session.next_request) is not None:
            requests.append((request.mode, request.pid))
            session.accept(())

        self.assertEqual(
            requests,
            [(0x01, 0x01), (0x03, None), (0x07, None), (0x0A, None)],
        )
        self.assertTrue(session.complete)
        self.assertIsNone(session.snapshot().mil_on)

    def test_incomplete_session_cannot_publish_a_snapshot(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "not complete"):
            Obd2DiagnosticsScanSession().snapshot()

    def test_scans_multi_ecu_healthy_vehicle(self) -> None:
        adapter = _Adapter({
            (0x01, 0x01): (
                Obd2Response(0x41, 0x01, bytes.fromhex("00040000"), 0x7E8),
                Obd2Response(0x41, 0x01, bytes.fromhex("00040000"), 0x7E9),
            ),
            (0x03, None): (Obd2Response(0x43, None, b"\x00", 0x7E8),),
            (0x07, None): (Obd2Response(0x47, None, b"\x00", 0x7E8),),
            (0x0A, None): (Obd2Response(0x4A, None, b"\x00", 0x7E8),),
        })

        snapshot = Obd2DiagnosticsScanner(adapter).scan()

        self.assertFalse(snapshot.mil_on)
        self.assertEqual(snapshot.stored_dtc_count, 0)
        self.assertTrue(snapshot.emissions_ready)
        self.assertEqual(snapshot.responding_ecus, (0x7E8, 0x7E9))
        self.assertEqual(snapshot.trouble_codes, ())

    def test_preserves_status_and_reporting_ecu_for_codes(self) -> None:
        adapter = _Adapter({
            (0x01, 0x01): (
                Obd2Response(0x41, 0x01, bytes.fromhex("81000000"), 0x7E8),
            ),
            (0x03, None): (
                Obd2Response(0x43, None, bytes.fromhex("0302"), 0x7E8),
            ),
            (0x07, None): (
                Obd2Response(0x47, None, bytes.fromhex("0420"), 0x7E9),
            ),
            (0x0A, None): (),
        })

        snapshot = Obd2DiagnosticsScanner(adapter).scan()

        self.assertTrue(snapshot.mil_on)
        self.assertEqual(snapshot.stored_dtc_count, 1)
        self.assertEqual(
            [(item.code, item.status, item.ecu_id) for item in snapshot.trouble_codes],
            [
                ("P0302", Obd2DiagnosticStatus.STORED, 0x7E8),
                ("P0420", Obd2DiagnosticStatus.PENDING, 0x7E9),
            ],
        )

    def test_reports_unknown_when_monitor_status_has_no_response(self) -> None:
        snapshot = Obd2DiagnosticsScanner(_Adapter({})).scan()

        self.assertIsNone(snapshot.mil_on)
        self.assertIsNone(snapshot.stored_dtc_count)
        self.assertIsNone(snapshot.emissions_ready)
        self.assertEqual(snapshot.responding_ecus, ())
        self.assertEqual(snapshot.trouble_codes, ())

    def test_manager_advances_scan_inside_normal_request_budget(self) -> None:
        adapter = _Adapter({
            (0x01, 0x01): (
                Obd2Response(0x41, 0x01, bytes.fromhex("81000000"), 0x7E8),
            ),
            (0x03, None): (
                Obd2Response(0x43, None, bytes.fromhex("0302"), 0x7E8),
            ),
        })
        manager = Obd2Manager(adapter)
        result = []
        thread = threading.Thread(target=lambda: result.append(manager.scan_diagnostics()))
        thread.start()
        deadline = time.monotonic() + 1.0
        while manager._diagnostics_session is None and time.monotonic() < deadline:
            time.sleep(0.001)

        for _ in range(4):
            before = len(adapter.requests)
            manager.read_state()
            self.assertEqual(len(adapter.requests), before + 1)

        thread.join(1.0)
        self.assertFalse(thread.is_alive())
        self.assertEqual(result[0].trouble_codes[0].code, "P0302")
        self.assertEqual(
            adapter.requests,
            [(0x01, 0x01), (0x03, None), (0x07, None), (0x0A, None)],
        )


if __name__ == "__main__":
    unittest.main()
