# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

from apps.launchers.app_launcher_if import AppLauncherIf, StatusCallback
from apps.launchers.external_window_manager import ExternalWindowManager, x11_environment
from apps.launchers.process_manager import close_matching_display_apps, is_process_running, terminate_process
from common.logging.logging_paths import logging_file_path


class BrowserKioskLauncher(AppLauncherIf):
    """Launch and orchestrate one browser window on a selected X display."""

    def __init__(self, *, url: str, process_pattern: str | None = None, log_file: str | Path | None = None, browser_candidates: tuple[str, ...] = ("chromium-browser", "chromium", "google-chrome"), kiosk: bool = True, app_mode: bool = False, profile_path: str | Path | None = None, window_position: tuple[int, int] | None = None, window_size: tuple[int, int] | None = None, startup_grace_seconds: float = 0.0, extra_arguments: tuple[str, ...] = (), window_class: str | None = None, exclusive_group: str | None = None, window_manager: ExternalWindowManager | None = None) -> None:
        if kiosk and app_mode:
            raise ValueError("kiosk and app_mode cannot both be enabled")
        if startup_grace_seconds < 0:
            raise ValueError("startup_grace_seconds cannot be negative")
        self.url = url
        self.process_pattern = process_pattern or url
        self.log_file = Path(log_file or logging_file_path("openroadcode", "browser.log"))
        self.browser_candidates = browser_candidates
        self.kiosk = kiosk
        self.app_mode = app_mode
        self.profile_path = Path(profile_path).expanduser() if profile_path is not None else None
        self.window_position = window_position
        self.window_size = window_size
        self.startup_grace_seconds = startup_grace_seconds
        self.extra_arguments = extra_arguments
        self.window_class = window_class
        self.exclusive_group = exclusive_group
        self._window_manager = window_manager or ExternalWindowManager()
        self._process: subprocess.Popen[str] | None = None
        self._window_id: str | None = None
        self._hidden = False

    def set_url(self, url: str) -> None:
        """Change the URL used by the next browser launch.

        A running Chromium instance is intentionally not navigated implicitly;
        callers that need a different page must stop it first so lifecycle and
        visibility state remain deterministic.
        """
        if not url.strip():
            raise ValueError("url must be non-empty")
        if self.is_running():
            raise RuntimeError("Cannot change browser URL while it is running")
        self.url = url

    def is_running(self) -> bool:
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None
            self._window_id = None
            self._hidden = False
        return is_process_running(self.process_pattern)

    def configure_app_window(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        width, height = size
        if width <= 0 or height <= 0:
            raise ValueError("size values must be positive")
        self.kiosk = False
        self.app_mode = True
        self.window_position = position
        self.window_size = size
        self.startup_grace_seconds = max(self.startup_grace_seconds, 0.2)

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        if self.is_running():
            self.show(remote_display, set_status)
            return
        self._window_id = None
        self._hidden = False
        browser_path = self._find_browser()
        environment = x11_environment(remote_display)
        command = [browser_path, "--noerrdialogs", "--disable-infobars", "--disable-session-crashed-bubble", "--disable-restore-session-state"]
        if _is_termux():
            command.append("--password-store=basic")
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
            self._process = subprocess.Popen(command, env=environment, stdout=log_handle, stderr=subprocess.STDOUT, start_new_session=True, text=True)
        finally:
            log_handle.close()
        if self.startup_grace_seconds:
            time.sleep(self.startup_grace_seconds)
            return_code = self._process.poll()
            if return_code is not None:
                self._process = None
                raise RuntimeError(f"Browser exited during startup (status {return_code}); see {self.log_file}")
        self._fit_app_window(remote_display)
        _status(set_status, f"Browser launched on {remote_display}")

    def show(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        if not self.is_running():
            return False
        self._activate_existing_window(remote_display)
        self._hidden = False
        _status(set_status, "Browser window activated")
        return True

    def hide(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        if not self.is_running():
            return False
        self._ensure_window_id(remote_display)
        hidden = self._window_manager.hide(display=remote_display, window_id=self._window_id)
        if hidden:
            self._hidden = True
            _status(set_status, "Browser hidden")
        return hidden

    def stop(self, remote_display: str, set_status: StatusCallback = None) -> None:
        process = self._process
        closed_normally = False
        if process is not None:
            close_requested = self._close_app_window(remote_display)
            if close_requested:
                self._wait_for_process_exit(process)
                closed_normally = process.poll() is not None
        if process is not None and not closed_normally:
            terminate_process(process)
        self._process = None
        self._window_id = None
        self._hidden = False
        if not closed_normally:
            close_matching_display_apps(display=remote_display, patterns=(self.process_pattern,))
        _status(set_status, "Browser stopped")

    def toggle(self, remote_display: str, set_status: StatusCallback = None) -> bool:
        if self.is_running() and not self._hidden:
            if self.hide(remote_display, set_status):
                return False
            self.stop(remote_display, set_status)
            return False
        if self.is_running():
            return self.show(remote_display, set_status)
        self.launch(remote_display, set_status)
        return True

    def _close_app_window(self, display: str) -> bool:
        return self._window_manager.close(display=display, window_id=self._window_id)

    @staticmethod
    def _wait_for_process_exit(process: subprocess.Popen[str], timeout_seconds: float = 3.0) -> None:
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            pass

    def _find_browser(self) -> str:
        for candidate in self.browser_candidates:
            browser = shutil.which(candidate)
            if browser:
                return browser
        names = ", ".join(self.browser_candidates)
        raise RuntimeError(f"No supported browser found in PATH. Tried: {names}")

    def _fit_app_window(self, display: str) -> None:
        if not (self.app_mode or self.kiosk) or self.window_class is None or self.window_position is None or self.window_size is None:
            return
        self._window_id = self._window_manager.fit(display=display, window_class=self.window_class, position=self.window_position, size=self.window_size)

    def _ensure_window_id(self, display: str) -> None:
        if self._window_id is None and self.window_class is not None:
            self._window_id = self._window_manager.wait_for_window_id(display=display, window_class=self.window_class)

    def _activate_existing_window(self, display: str) -> None:
        if self.window_class is None:
            return
        self._window_id = self._window_manager.activate(display=display, window_class=self.window_class)


def _is_termux() -> bool:
    return bool(os.getenv("TERMUX_VERSION")) or os.getenv("PREFIX", "").startswith("/data/data/com.termux/")


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
