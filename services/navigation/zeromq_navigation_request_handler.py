# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""NavigationRequestHandlerIf implementation backed by ZeroMQ REQ/REP."""

from __future__ import annotations

import zmq

from services.navigation.navigation_command_service import (
    CALIBRATE_STATIONARY_COMMAND,
    RESET_HEADING_COMMAND,
)
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
)
from ui.navigation.navigation_request_handler_if import NavigationRequestHandlerIf


class NavigationCommandError(RuntimeError):
    """Raised when a remote navigation command is rejected or times out."""


class ZeroMqNavigationRequestHandler(NavigationRequestHandlerIf):
    """Send navigation UI commands to the navigation-owner process."""

    def __init__(
        self,
        endpoint: str = DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
        *,
        timeout_ms: int = 2000,
    ) -> None:
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero")
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.setsockopt(zmq.LINGER, 0)
        self._socket.setsockopt(zmq.RCVTIMEO, timeout_ms)
        self._socket.setsockopt(zmq.SNDTIMEO, timeout_ms)
        self._socket.connect(endpoint)

    def request_stationary_calibration(self) -> None:
        """Request stationary calibration from the navigation-owner process."""
        self._request(CALIBRATE_STATIONARY_COMMAND)

    def request_heading_reset(self) -> None:
        """Request a zero-degree relative heading reset."""
        self._request(RESET_HEADING_COMMAND)

    def close(self) -> None:
        """Release ZeroMQ resources owned by this client."""
        self._socket.close(linger=0)
        self._context.term()

    def _request(self, command: str) -> None:
        try:
            self._socket.send_json({"command": command, "arguments": {}})
            response = self._socket.recv_json()
        except zmq.Again as error:
            raise NavigationCommandError(
                f"Navigation command timed out: {command}"
            ) from error

        if not isinstance(response, dict):
            raise NavigationCommandError("Navigation command returned an invalid response")
        if not response.get("ok", False):
            raise NavigationCommandError(
                str(response.get("message", "Navigation command failed"))
            )
