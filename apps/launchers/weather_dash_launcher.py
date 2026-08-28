# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

from apps.launchers.app_launcher_if import StatusCallback
from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.streamlit_launcher import StreamlitLauncher
from common.logging.logging_paths import logging_file_path
from controllers.weather import DEFAULT_WEATHER_CACHE_DIRECTORY


class WeatherDashLauncher(StreamlitLauncher):
    """Launch the standalone weather dashboard application."""

    def __init__(
        self,
        *,
        project_root: str | Path | None = None,
        port: int = 8501,
        cache_directory: str | Path = DEFAULT_WEATHER_CACHE_DIRECTORY,
        refresh_seconds: int = 120,
        browser: BrowserKioskLauncher | None = None,
    ) -> None:
        root = Path(project_root).expanduser().resolve() if project_root is not None else Path(__file__).resolve().parents[2]

        super().__init__(
            app_path=root / "apps" / "weatherDash" / "main.py",
            port=port,
            log_file=logging_file_path("openroadcode", "weather-dashboard.log"),
            browser_log_file=logging_file_path("openroadcode", "weather-dashboard-browser.log"),
            browser_exclusive_group="openroadcode-auxiliary-dashboard",
            environment={
                "OPENROAD_WEATHER_CACHE_DIRECTORY": str(Path(cache_directory).expanduser()),
                "OPENROAD_WEATHER_REFRESH_SECONDS": str(refresh_seconds),
            },
            browser=browser,
        )

    def launch(self, remote_display: str, set_status: StatusCallback = None) -> None:
        if set_status is not None:
            set_status("Launching weather dashboard...")
        super().launch(remote_display, set_status)
