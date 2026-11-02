# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Semantic request to open Waze using the configured native or browser view."""
from typing import Protocol


class WazeRequestHandlerIf(Protocol):
    def request_open_waze(self) -> None:
        """Open Waze when online without changing the active ORC route."""
        ...
