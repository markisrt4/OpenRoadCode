# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation tests for the automotive-service diagnostics CLI."""

from controllers.automotive.obd2 import (
    Obd2DiagnosticStatus,
    Obd2DiagnosticTroubleCode,
    Obd2DiagnosticsSnapshot,
)
from controllers.automotive.obd2.component_test.obd2_diagnostics_cli import (
    print_snapshot,
)


def test_cli_prints_service_snapshot(capsys) -> None:
    print_snapshot(
        Obd2DiagnosticsSnapshot(
            mil_on=True,
            stored_dtc_count=1,
            emissions_ready=False,
            responding_ecus=(0x7E8,),
            trouble_codes=(
                Obd2DiagnosticTroubleCode(
                    "P0302", Obd2DiagnosticStatus.STORED, 0x7E8
                ),
            ),
        )
    )

    output = capsys.readouterr().out
    assert "MIL: ON" in output
    assert "Emissions monitors: NOT READY" in output
    assert "Stored DTCs: P0302 (ECU 0x7E8)" in output
