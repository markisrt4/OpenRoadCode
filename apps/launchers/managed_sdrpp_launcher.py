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
        # A previous ORC session can leave an SDR++ process behind after RigCTL
        # has stopped responding. Treat that as stale ownership rather than
        # waiting on a process that cannot satisfy the radio contract.
        if self.is_running() and not self.is_rigctl_ready():
            if set_status is not None:
                set_status("Recovering stale SDR++ process...")
            self.stop(remote_display, set_status)
            time.sleep(0.25)

        # SDRPPLauncher waits for RigCTL before returning. Watch for the X11
        # client concurrently and unmap it as soon as the process owns a window.
        watcher = threading.Thread(
            target=self._hide_when_window_appears,
            name="sdrpp-preload-window-hide",
            daemon=True,
        )
        watcher.start()
        super().launch(remote_display, set_status)

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        # Process existence and application readiness are different states.
        # If RigCTL is unavailable, let AppRuntimeManager fall through to
        # launch(), which performs stale-process recovery above.
        if not self.is_rigctl_ready():
            return False
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
                subprocess.run(
                    ["xdotool", "windowunmap", str(window_id)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return
            time.sleep(0.01)

    def _window_id(self) -> int | None:
        if shutil.which("xdotool") is None:
            return None

        if self._process is not None and self._process.poll() is None:
            try:
                process_id = self.window_process_id(timeout_seconds=0.02)
            except RuntimeError:
                process_id = None
            if process_id is not None:
                window_id = self._search_window("--pid", str(process_id))
                if window_id is not None:
                    return window_id

        for window_class in ("sdrpp", "SDR++"):
            window_id = self._search_window("--class", window_class)
            if window_id is not None:
                return window_id

        return self._search_window("--name", r"SDR\+\+")

    @staticmethod
    def _search_window(selector: str, value: str) -> int | None:
        result = subprocess.run(
            ["xdotool", "search", selector, value],
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
