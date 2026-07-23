from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeAlias, runtime_checkable


StatusCallback: TypeAlias = Callable[[str], None] | None


@runtime_checkable
class AppLauncherIf(Protocol):
    """Thread-compatible interface for launching external applications.

    Implementations may perform process management synchronously, but their
    methods must be safe to invoke from a worker thread.
    """

    def launch(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Launch the application.

        @param remote_display Display identifier to pass to the application.
        @param set_status Optional callback for user-visible status messages.
        """
        ...

    def stop(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Stop the application.

        @param remote_display Display on which the application is running.
        @param set_status Optional callback for user-visible status messages.
        """
        ...

    def toggle(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> bool:
        """Toggle the application's running state.

        @param remote_display Display on which to launch or stop the app.
        @param set_status Optional callback for user-visible status messages.
        @return ``True`` when the application is running after the operation.
        """
        ...

    def is_running(self) -> bool:
        """Return whether the application is currently running.

        @retval True The managed application is running.
        @retval False No matching application is running.
        """
        ...
