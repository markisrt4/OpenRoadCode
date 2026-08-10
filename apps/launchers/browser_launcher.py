from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    StatusCallback,
)
from apps.launchers.process_manager import (
    close_matching_display_apps,
    is_process_running,
    terminate_process,
)
from common.logging.logging_paths import logging_file_path


class BrowserKioskLauncher(AppLauncherIf):
    """Launch a browser in kiosk mode on a selected X display."""

    _exclusive_launchers: dict[
        tuple[str, str],
        "BrowserKioskLauncher",
    ] = {}

    def __init__(
        self,
        *,
        url: str,
        process_pattern: str | None = None,
        log_file: str | Path | None = None,
        browser_candidates: tuple[str, ...] = (
            "chromium-browser",
            "chromium",
            "google-chrome",
        ),
        kiosk: bool = True,
        app_mode: bool = False,
        profile_path: str | Path | None = None,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
        startup_grace_seconds: float = 0.0,
        extra_arguments: tuple[str, ...] = (),
        window_class: str | None = None,
        exclusive_group: str | None = None,
    ) -> None:
        if kiosk and app_mode:
            raise ValueError("kiosk and app_mode cannot both be enabled")
        if startup_grace_seconds < 0:
            raise ValueError("startup_grace_seconds cannot be negative")
        self.url = url
        self.process_pattern = process_pattern or url
        self.log_file = Path(
            log_file
            or logging_file_path(
                "openroadcode",
                "browser.log",
            )
        )
        self.browser_candidates = browser_candidates
        self.kiosk = kiosk
        self.app_mode = app_mode
        self.profile_path = (
            Path(profile_path).expanduser()
            if profile_path is not None
            else None
        )
        self.window_position = window_position
        self.window_size = window_size
        self.startup_grace_seconds = startup_grace_seconds
        self.extra_arguments = extra_arguments
        self.window_class = window_class
        self.exclusive_group = exclusive_group
        self._process: subprocess.Popen[str] | None = None
        self._window_id: str | None = None

    def is_running(self) -> bool:
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None

        return is_process_running(self.process_pattern)

    def configure_app_window(
        self,
        *,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> None:
        """Configure a browser app window aligned to a UI panel."""
        width, height = size
        if width <= 0 or height <= 0:
            raise ValueError("size values must be positive")
        self.kiosk = False
        self.app_mode = True
        self.window_position = position
        self.window_size = size
        self.startup_grace_seconds = max(
            self.startup_grace_seconds,
            0.2,
        )

    def launch(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        if self.is_running():
            self._activate_existing_window(
                _x11_environment(remote_display)
            )
            _status(set_status, "Browser already running; window activated")
            return

        self._close_exclusive_peer(remote_display)
        self._window_id = None

        browser_path = self._find_browser()
        environment = _x11_environment(remote_display)
        command = [
            browser_path,
            "--noerrdialogs",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-restore-session-state",
        ]
        if self.kiosk:
            command.append("--kiosk")
        if self.app_mode:
            command.append(f"--app={self.url}")
        if self.profile_path is not None:
            self.profile_path.mkdir(parents=True, exist_ok=True)
            self.profile_path.chmod(0o700)
            command.append(f"--user-data-dir={self.profile_path}")
        if self.window_position is not None:
            x, y = self.window_position
            command.append(f"--window-position={x},{y}")
        if self.window_size is not None:
            width, height = self.window_size
            if width <= 0 or height <= 0:
                raise ValueError("window_size values must be positive")
            command.append(f"--window-size={width},{height}")
        command.extend(self.extra_arguments)
        if self.window_class is not None:
            command.append(f"--class={self.window_class}")
        if not self.app_mode:
            command.append(self.url)

        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                command,
                env=environment,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        finally:
            log_handle.close()

        if self.startup_grace_seconds:
            time.sleep(self.startup_grace_seconds)
            return_code = self._process.poll()
            if return_code is not None:
                self._process = None
                raise RuntimeError(
                    "Browser exited during startup "
                    f"(status {return_code}); see {self.log_file}"
                )

        self._fit_app_window(environment)
        if self.exclusive_group is not None:
            self._exclusive_launchers[
                (self.exclusive_group, remote_display)
            ] = self
        _status(set_status, f"Browser launched on {remote_display}")

    def stop(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        process = self._process
        closed_normally = False
        if process is not None:
            close_requested = self._close_app_window(
                _x11_environment(remote_display)
            )
            if close_requested:
                self._wait_for_process_exit(process)
                closed_normally = process.poll() is not None

        if process is not None and not closed_normally:
            terminate_process(process)

        self._process = None
        self._window_id = None
        if self.exclusive_group is not None:
            key = (self.exclusive_group, remote_display)
            if self._exclusive_launchers.get(key) is self:
                self._exclusive_launchers.pop(key, None)

        if not closed_normally:
            close_matching_display_apps(
                display=remote_display,
                patterns=(self.process_pattern,),
            )
        _status(set_status, "Browser stopped")

    def _close_exclusive_peer(self, display: str) -> None:
        group = self.exclusive_group
        if group is None:
            return
        peer = self._exclusive_launchers.get((group, display))
        if peer is not None and peer is not self:
            peer.stop(display)

    def _close_app_window(self, environment: dict[str, str]) -> bool:
        """Ask the window manager to close Chromium so it can save its profile."""
        if self._window_id is None or shutil.which("wmctrl") is None:
            return False

        subprocess.run(
            ["wmctrl", "-ic", self._window_id],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return True

    @staticmethod
    def _wait_for_process_exit(
        process: subprocess.Popen[str],
        timeout_seconds: float = 3.0,
    ) -> None:
        """Allow a normally closed browser time to flush cookies and state."""
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            pass

    def toggle(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> bool:
        if self.is_running():
            self.stop(remote_display, set_status)
            return False

        self.launch(remote_display, set_status)
        return True

    def _find_browser(self) -> str:
        for candidate in self.browser_candidates:
            browser = shutil.which(candidate)
            if browser:
                return browser

        names = ", ".join(self.browser_candidates)
        raise RuntimeError(
            f"No supported browser found in PATH. Tried: {names}"
        )

    def _fit_app_window(self, environment: dict[str, str]) -> None:
        if (
            not (self.app_mode or self.kiosk)
            or self.window_class is None
            or self.window_position is None
            or self.window_size is None
            or shutil.which("wmctrl") is None
            or shutil.which("xprop") is None
        ):
            return

        window_id = self._wait_for_window_id(environment)
        if window_id is None:
            return
        self._window_id = window_id

        subprocess.run(
            [
                "wmctrl",
                "-ir",
                window_id,
                "-b",
                "remove,fullscreen",
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(0.1)
        subprocess.run(
            [
                "wmctrl",
                "-ir",
                window_id,
                "-b",
                "remove,maximized_vert,maximized_horz",
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(0.1)
        subprocess.run(
            [
                "xprop",
                "-id",
                window_id,
                "-f",
                "_MOTIF_WM_HINTS",
                "32c",
                "-set",
                "_MOTIF_WM_HINTS",
                "2, 0, 0, 0, 0",
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(0.1)
        x, y = self.window_position
        width, height = self.window_size
        subprocess.run(
            [
                "wmctrl",
                "-ir",
                window_id,
                "-e",
                f"0,{x},{y},{width},{height}",
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _activate_existing_window(
        self,
        environment: dict[str, str],
    ) -> None:
        """Raise an existing owned browser window when it is reopened."""
        if self.window_class is None or shutil.which("wmctrl") is None:
            return
        window_id = self._wait_for_window_id(environment)
        if window_id is None:
            return
        self._window_id = window_id
        subprocess.run(
            ["wmctrl", "-ia", window_id],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    def _wait_for_window_id(
        self,
        environment: dict[str, str],
    ) -> str | None:
        expected_class = self.window_class.casefold()
        deadline = time.monotonic() + 3.0
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


def _x11_environment(display: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DISPLAY": display,
            "XDG_SESSION_TYPE": "x11",
            "GDK_BACKEND": "x11",
        }
    )
    return environment


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
