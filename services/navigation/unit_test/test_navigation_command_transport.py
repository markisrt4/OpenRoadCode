# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import socket
import threading
from unittest.mock import Mock

from services.navigation.navigation_command_service import NavigationCommandService
from services.navigation.zeromq_navigation_command_server import ZeroMqNavigationCommandServer
from services.navigation.zeromq_navigation_request_handler import ZeroMqNavigationRequestHandler


def _free_tcp_endpoint() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return f"tcp://127.0.0.1:{sock.getsockname()[1]}"


def test_request_handler_commands_same_controller_owned_by_service():
    controller = Mock()
    endpoint = _free_tcp_endpoint()
    server = ZeroMqNavigationCommandServer(
        NavigationCommandService(controller),
        endpoint,
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    client = ZeroMqNavigationRequestHandler(endpoint, timeout_ms=1000)

    try:
        client.request_stationary_calibration()
        client.request_heading_reset()
    finally:
        client.close()
        server.close()
        thread.join(timeout=1.0)

    controller.calibrate_stationary.assert_called_once_with(
        sample_count=100,
        sample_interval_s=0.01,
    )
    controller.reset_heading.assert_called_once_with(0.0)
