# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Semantic request to open Waze using the configured native or browser view."""
from typing import Protocol
from ui.navigation import GeoPoint


class WazeRequestHandlerIf(Protocol):
    def request_open_waze(self) -> None:
        """Open Waze when online without changing the active ORC route."""
        ...

    def request_navigate_waze(self, destination: GeoPoint) -> None:
        """Hand an SI destination to native Waze without changing the ORC route."""
        ...
