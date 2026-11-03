# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Semantic requests for native Android Waze navigation and session lifetime."""
from typing import Protocol
from dataclasses import dataclass
from ui.navigation import GeoPoint


@dataclass(frozen=True)
class WazeSessionState:
    active: bool = False
    closing: bool = False
    launching: bool = False


class WazeRequestHandlerIf(Protocol):
    def request_open_waze(self) -> None:
        """Open or restore native Waze without changing the active ORC route."""
        ...

    def request_navigate_waze(self, destination: GeoPoint) -> None:
        """Hand an SI destination to native Waze without changing the ORC route."""
        ...

    def request_close_waze(self) -> None:
        """Explicitly stop the Waze session; ordinary navigation only hides it."""
        ...

    def request_navigate_saved_destination(self, key: str) -> None:
        """Use ORC's current saved Home/Work coordinates, without account sync."""
        ...
