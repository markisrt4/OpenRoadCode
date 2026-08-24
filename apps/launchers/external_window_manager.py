# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Manage presentation of externally launched X11 application windows."""

from __future__ import annotations

import os
import shutil
import subprocess
import time


class ExternalWindowManager:
    """Find, position, activate, and close external X11 windows by class."""

    def __init__(self, *, window_timeout_seconds: float = 3.0) -> None:
        if window_timeout_seconds <= 0.0:
            raise ValueError("window_timeout_seconds must be greater than zero")
        self._window_timeout_seconds = window_timeout_seconds

    def fit(
        self,
        *,
        display: str,
        window_class: str,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> str | None:
        """Fit a matching undecorated window to the requested rectangle."""
        width, height = size
        if width <= 0 or height <= 0:
            raise ValueError("size values must be positive")
        if not self._tools_available("wmctrl", "xprop"):
            return None

        environment = x11_environment(display)
        window_id = self.wait_for_window_id(
            display=display,
            window_class=window_class,
        )
        if window_id is None:
            return None

        self._run(
            ["wmctrl", "-ir", window_id, "-b", "remove,fullscreen"],
            environment,
        )
        time.sleep(0.1)
        self._run(
            [
                "wmctrl", "-ir", window_id, "-b",
                "remove,maximized_vert,maximized_horz",
            ],
            environment,
        )
        time.sleep(0.1)
        self._run(
            [
                "xprop", "-id", window_id,
                "-f", "_MOTIF_WM_HINTS", "32c",
                "-set", "_MOTIF_WM_HINTS", "2, 0, 0, 0, 0",
            ],
            environment,
        )
        time.sleep(0.1)
        x, y = position
        self._run(
            ["wmctrl", "-ir", window_id, "-e", f"0,{x},{y},{width},{height}"],
            environment,
        )
        return window_id

    def activate(self, *, display: str, window_class: str) -> str | None:
        """Raise and focus a matching external window."""
        if not self._tools_available("wmctrl"):
            return None
        window_id = self.wait_for_window_id(
            display=display,
            window_class=window_class,
        )
        if window_id is None:
            return None
        self._run(
            ["wmctrl", "-ia", window_id],
            x11_environment(display),
        )
        return window_id

    def close(self, *, display: str, window_id: str | None) -> bool:
        """Ask the window manager to close an identified external window."""
        if window_id is None or not self._tools_available("wmctrl"):
            return False
        self._run(
            ["wmctrl", "-ic", window_id],
            x11_environment(display),
        )
        return True

    def wait_for_window_id(self, *, display: str, window_class: str) -> str | None:
        """Wait briefly for a window whose WM_CLASS contains window_class."""
        if not self._tools_available("wmctrl"):
            return None
        expected_class = window_class.casefold()
        environment = x11_environment(display)
        deadline = time.monotonic() + self._window_timeout_seconds
        while time.monotonic() < deadline:
            result = subprocess.run(
                ["wmctrl", "-lx"],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
            for line in result.stdout.splitlines():
                fields = line.split(maxsplit=4)
                if len(fields) >= 3 and expected_class in fields[2].casefold():
                    return fields[0]
            time.sleep(0.1)
        return None

    @staticmethod
    def _tools_available(*commands: str) -> bool:
        return all(shutil.which(command) is not None for command in commands)

    @staticmethod
    def _run(command: list[str], environment: dict[str, str]) -> None:
        subprocess.run(
            command,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def x11_environment(display: str) -> dict[str, str]:
    """Return an environment forcing an external application onto X11."""
    environment = os.environ.copy()
    environment.update(
        {
            "DISPLAY": display,
            "XDG_SESSION_TYPE": "x11",
            "GDK_BACKEND": "x11",
        }
    )
    return environment
