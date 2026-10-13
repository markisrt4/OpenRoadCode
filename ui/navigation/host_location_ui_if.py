# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Presentation and semantic requests for host location permission."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class HostLocationState:
    status: str = "Browser permission is required. Bridge/GPS takes priority."
    busy: bool = False
    can_share: bool = True


class HostLocationUiIf(Protocol):
    def set_host_location_state(self, state: HostLocationState) -> None:
        """Present permission-page availability, never infer browser consent."""
        ...


class HostLocationRequestHandlerIf(Protocol):
    def show(self) -> None:
        """Activate the host location settings surface."""
        ...

    def hide(self) -> None:
        """Invalidate work belonging to the hidden settings surface."""
        ...

    def share_host_location(self) -> None:
        """Open the permission page after checking the local service."""
        ...
