# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Connectivity preference contract shared by frontend presentation."""
from collections.abc import Callable
from typing import Protocol


class OnlineModeIf(Protocol):
    """Read effective mode and subscribe to presentation changes."""

    @property
    def online(self) -> bool:
        """Return effective connectivity.

        @return Whether online actions are allowed."""
        ...

    @property
    def requested_online(self) -> bool:
        """Return saved preference.

        @return Whether online mode was requested."""
        ...

    def subscribe(self, listener: Callable[[bool], None]) -> Callable[[], None]:
        """Observe mode.

        @param listener Callback.

        @return Unsubscribe callback."""
        ...
