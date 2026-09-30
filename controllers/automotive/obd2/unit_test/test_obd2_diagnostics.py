# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for generic OBD-II diagnostic scanning."""

import unittest

from controllers.automotive.obd2.obd2_diagnostics import (
    Obd2DiagnosticStatus,
    Obd2DiagnosticsScanner,
)
from protocols.obd2 import Obd2AdapterIf, Obd2Error, Obd2Request, Obd2Response


class _Adapter(Obd2AdapterIf):
    def __init__(self, responses):
        self.responses = responses

    @property
    def is_connected(self) -> bool:
        return True

    def connect(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def request(self, request: Obd2Request) -> tuple[Obd2Response, ...]:
        response = self.responses.get((request.mode, request.pid), ())
        if isinstance(response, Exception):
            raise response
        return response


class Obd2DiagnosticsScannerTest(unittest.TestCase):
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

    def test_optional_service_failure_does_not_discard_other_results(self) -> None:
        adapter = _Adapter({
            (0x01, 0x01): (
                Obd2Response(0x41, 0x01, bytes.fromhex("81000000"), 0x7E8),
            ),
            (0x03, None): (
                Obd2Response(0x43, None, bytes.fromhex("0302"), 0x7E8),
            ),
            (0x07, None): (),
            (0x0A, None): Obd2Error("service unsupported"),
        })

        snapshot = Obd2DiagnosticsScanner(adapter).scan()

        self.assertTrue(snapshot.mil_on)
        self.assertEqual(snapshot.stored_dtc_count, 1)
        self.assertEqual(
            [(item.code, item.status) for item in snapshot.trouble_codes],
            [("P0302", Obd2DiagnosticStatus.STORED)],
        )

    def test_reports_unknown_when_monitor_status_has_no_response(self) -> None:
        snapshot = Obd2DiagnosticsScanner(_Adapter({})).scan()

        self.assertIsNone(snapshot.mil_on)
        self.assertIsNone(snapshot.stored_dtc_count)
        self.assertIsNone(snapshot.emissions_ready)
        self.assertEqual(snapshot.responding_ecus, ())
        self.assertEqual(snapshot.trouble_codes, ())


if __name__ == "__main__":
    unittest.main()
