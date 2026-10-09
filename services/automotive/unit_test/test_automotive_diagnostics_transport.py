# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integration coverage for the automotive diagnostics command transport."""

import socket
import threading
import time

from controllers.automotive.obd2 import (
    Obd2DiagnosticStatus,
    Obd2DiagnosticTroubleCode,
    Obd2DiagnosticsSnapshot,
)
from services.automotive.automotive_diagnostics_client import AutomotiveDiagnosticsClient
from services.automotive.automotive_diagnostics_command_service import (
    AutomotiveDiagnosticsCommandService,
)
from services.automotive.zeromq_automotive_command_server import (
    ZeroMqAutomotiveCommandServer,
)


class _Source:
    def scan_diagnostics(self):
        return Obd2DiagnosticsSnapshot(
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


def _free_endpoint() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return f"tcp://127.0.0.1:{sock.getsockname()[1]}"


def test_cli_client_receives_service_owned_semantic_snapshot() -> None:
    endpoint = _free_endpoint()
    server = ZeroMqAutomotiveCommandServer(
        AutomotiveDiagnosticsCommandService(_Source()), endpoint
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 1.0
    while not server.is_running and time.monotonic() < deadline:
        time.sleep(0.01)
    assert server.is_running
    try:
        snapshot = AutomotiveDiagnosticsClient(endpoint, timeout_ms=1000).scan()
    finally:
        server.close()
        thread.join(1.0)

    assert snapshot.mil_on is True
    assert snapshot.trouble_codes[0].code == "P0302"
    assert not thread.is_alive()
