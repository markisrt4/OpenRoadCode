# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""SDR++ launcher with window visibility operations for runtime management."""

from __future__ import annotations

import shutil
import subprocess
import threading
import time

from apps.launchers.app_launcher_if import StatusCallback
from apps.launchers.sdrpp_launcher import SDRPPLauncher


class ManagedSDRPPLauncher(SDRPPLauncher):
    """Allow ``AppRuntimeManager`` to keep SDR++ warm but out of sight."""

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        # SDRPPLauncher waits for RigCTL before returning. Start a small X11
        # watcher first so the native window is unmapped as soon as it appears,
        # rather than flashing over the already-running ORC UI during preload.
        watcher = threading.Thread(
            target=self._hide_when_window_appears,
            name="sdrpp-preload-window-hide",
            daemon=True,
        )
        watcher.start()
        super().launch(remote_display, set_status)

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        del remote_display
        window_id = self._window_id()
        if window_id is None:
            return False
        subprocess.run(["xdotool", "windowmap", str(window_id)], check=False)
        if set_status is not None:
            set_status("SDR++ ready")
        return True

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        del remote_display
        window_id = self._window_id()
        if window_id is None:
            return False
        subprocess.run(["xdotool", "windowunmap", str(window_id)], check=False)
        if set_status is not None:
            set_status("SDR++ preloaded")
        return True

    def _hide_when_window_appears(self) -> None:
        deadline = time.monotonic() + self.rigctl_timeout_seconds
        while time.monotonic() < deadline:
            window_id = self._window_id()
            if window_id is not None:
                subprocess.run(["xdotool", "windowunmap", str(window_id)], check=False)
                return
            time.sleep(0.05)

    @staticmethod
    def _window_id() -> int | None:
        if shutil.which("xdotool") is None:
            return None
        result = subprocess.run(
            ["xdotool", "search", "--name", r"SDR\+\+"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        candidates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not candidates:
            return None
        try:
            return int(candidates[-1])
        except ValueError:
            return None
