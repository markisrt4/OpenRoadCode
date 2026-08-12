# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import subprocess
import os
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from apps.launchers.app_launcher_if import (
    AppLauncherIf,
    StatusCallback,
)
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.process_manager import (
    is_process_running,
    terminate_process,
)
from common.logging.logging_paths import logging_file_path


class StreamlitLauncher(AppLauncherIf):
    """Launch a Streamlit server and its kiosk browser."""

    def __init__(
        self,
        *,
        app_path: str | Path,
        port: int = 8501,
        log_file: str | Path | None = None,
        browser_log_file: str | Path | None = None,
        startup_timeout_seconds: float = 10.0,
        browser_exclusive_group: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> None:
        self.app_path = Path(app_path).expanduser().resolve()
        self.port = port
        self.log_file = Path(
            log_file
            or logging_file_path(
                "openroadcode",
                "streamlit.log",
            )
        )
        self.startup_timeout_seconds = startup_timeout_seconds
        self.environment = dict(environment or {})
        self.browser = BrowserKioskLauncher(
            url=f"http://127.0.0.1:{port}",
            process_pattern=f"127.0.0.1:{port}",
            profile_path=(
                Path.home()
                / "snap"
                / "chromium"
                / "common"
                / f"openroadcode-streamlit-{port}"
            ),
            window_class=f"OpenRoadCodeStreamlit{port}",
            exclusive_group=browser_exclusive_group,
            log_file=(
                browser_log_file
                or logging_file_path(
                    "openroadcode",
                    "streamlit-browser.log",
                )
            ),
        )
        self._process: subprocess.Popen[str] | None = None
        self._start_lock = threading.Lock()

    @property
    def process_pattern(self) -> str:
        return str(self.app_path)

    def configure_browser_window(
        self,
        *,
        position: tuple[int, int],
        size: tuple[int, int],
    ) -> None:
        """Align the dashboard browser to a Car UI panel."""
        self.browser.configure_app_window(
            position=position,
            size=size,
        )

    def is_running(self) -> bool:
        if self._process is not None:
            if self._process.poll() is None:
                return True
            self._process = None

        return is_process_running(self.process_pattern)

    def launch(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        _status(
            set_status,
            f"Launching Streamlit app: {self.app_path.name}",
        )

        self.prepare()

        self.browser.launch(remote_display, set_status)
        _status(
            set_status,
            f"Streamlit dashboard launched on {remote_display}",
        )

    def prepare(self) -> None:
        """Start the Streamlit server without opening its browser.

        This method is safe to call from a background warm-up worker and is
        idempotent when the server is already running.
        """
        if not self.app_path.is_file():
            raise FileNotFoundError(
                f"Streamlit application not found: {self.app_path}"
            )
        with self._start_lock:
            if not self.is_running():
                self._start_server()
        self._wait_for_server()

    def stop(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        self.browser.stop(remote_display, None)

        if self._process is not None:
            terminate_process(self._process)
            self._process = None

        _status(set_status, "Streamlit dashboard stopped")

    def close_browser(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> None:
        """Close the browser while leaving the Streamlit server warm."""
        self.browser.stop(remote_display, None)
        _status(set_status, "Streamlit dashboard browser closed")

    def toggle(
        self,
        remote_display: str,
        set_status: StatusCallback = None,
    ) -> bool:
        if self.browser.is_running():
            self.stop(remote_display, set_status)
            return False

        self.launch(remote_display, set_status)
        return True

    def _start_server(self) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        log_handle = self.log_file.open("a", encoding="utf-8")
        try:
            self._process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "streamlit",
                    "run",
                    str(self.app_path),
                    "--server.headless",
                    "true",
                    "--server.port",
                    str(self.port),
                    "--browser.gatherUsageStats",
                    "false",
                ],
                env={**os.environ, **self.environment},
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                text=True,
            )
        finally:
            log_handle.close()

    def _wait_for_server(self) -> bool:
        deadline = time.monotonic() + self.startup_timeout_seconds
        url = f"http://127.0.0.1:{self.port}"
        while time.monotonic() < deadline:
            try:
                with urlopen(url, timeout=0.5) as response:
                    if 200 <= response.status < 500:
                        return True
            except (OSError, URLError):
                pass
            time.sleep(0.1)
        return False


def _status(callback: StatusCallback, message: str) -> None:
    if callback is not None:
        callback(message)
