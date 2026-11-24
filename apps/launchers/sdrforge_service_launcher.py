# SPDX-License-Identifier: MIT
"""Non-owning launcher facade for the shared SDRForge service."""

from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from ui.system.app_launcher_if import StatusCallback


class SdrForgeServiceLauncher:
    """Expose shared service readiness without owning USB or its lifetime."""

    def __init__(self, base_url: str = "http://127.0.0.1:5570", timeout: float = 1.0) -> None:
        self._health_url = base_url.rstrip("/") + "/v1/health"
        self._timeout = timeout

    def is_running(self) -> bool:
        try:
            with urlopen(self._health_url, timeout=self._timeout) as response:
                payload = json.load(response)
            return isinstance(payload, dict) and payload.get("status") == "ok"
        except (HTTPError, URLError, OSError, TimeoutError, ValueError):
            return False

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        del remote_display
        if not self.is_running():
            raise RuntimeError(
                "SDRForge service unavailable; start the managed service or "
                "complete Android-authorized USB handoff"
            )
        if set_status is not None:
            set_status("SDRForge service ready")

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        del remote_display
        # Screen retirement must not terminate a shared receiver service.
        if set_status is not None:
            set_status("SDRForge remains managed by its service")

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        self.launch(remote_display, set_status)
        return True
