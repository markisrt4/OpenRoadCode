# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from collections.abc import Callable

from apps.carUi.system.system_controller import SystemController


class SystemControlManager:
    """Coordinate system lifecycle operations with UI updates."""

    def __init__(
        self,
        *,
        system_controller: SystemController,
        set_status: Callable[[str], None],
        request_close: Callable[[], None],
    ) -> None:
        self._system_controller = system_controller
        self._set_status = set_status
        self._request_close = request_close

    def power_off(self) -> None:
        self._set_status("Shutting down OpenRoadCode apps...")

        try:
            self._system_controller.close_display_apps()
        except Exception as exc:
            self._set_status(f"Shutdown cleanup failed: {exc}")
            print(f"[SYSTEM] Shutdown cleanup failed: {exc}")
        finally:
            self._request_close()
