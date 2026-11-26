# SPDX-License-Identifier: MIT
"""Host-location permission and recovery adapter contract."""

from collections.abc import Callable
from typing import Protocol


class HostLocationServiceUnavailable(RuntimeError):
    """The browser-position endpoint is not currently available."""


class HostLocationPermissionIf(Protocol):
    def open_permission_page(self, cancelled: Callable[[], bool]) -> None:
        """Check service availability and open the host's ordinary browser.

        @param cancelled Callback reporting obsolete lifecycle work.
        """
        ...

    def restart_location_service(self, cancelled: Callable[[], bool]) -> None:
        """Restart the managed location service and wait until it is ready.

        @param cancelled Callback reporting obsolete lifecycle work.
        """
        ...
