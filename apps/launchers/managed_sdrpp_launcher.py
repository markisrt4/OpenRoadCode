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
        # SDRPPLauncher waits for RigCTL before returning. Watch for the X11
        # client concurrently and unmap it as soon as the process owns a window.
        # Looking up by PID is important here: SDR++ can map its window before
        # its final title is installed, which made name-based hiding visibly late.
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

        # Prefer the owning process because it is available before the window
        # manager/title state has completely settled. This is particularly
        # useful for the Termux proot launch path, where the actual SDR++ child
        # appears underneath the proot-distro wrapper.
        if self._process is not None and self._process.poll() is None:
            try:
                process_id = self.window_process_id(timeout_seconds=0.02)
            except RuntimeError:
                process_id = None
            if process_id is not None:
                window_id = self._search_window("--pid", str(process_id))
                if window_id is not None:
                    return window_id

        # Fall back to WM_CLASS before title. Some window managers publish the
        # class earlier than the final SDR++ title string.
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
