# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build browser launchers from user-facing application configuration."""

from __future__ import annotations

from pathlib import Path

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.external_window_manager import ExternalWindowManager
from config.application_config import ApplicationConfig, ApplicationsConfig, ApplicationType


class BrowserApplicationFactory:
    """Create browser launchers without leaking TOML details into UI composition."""

    def __init__(
        self,
        config: ApplicationsConfig,
        *,
        window_manager: ExternalWindowManager | None = None,
    ) -> None:
        self._config = config
        self._window_manager = window_manager

    def create(self, key: str) -> BrowserKioskLauncher:
        """Create the configured browser launcher identified by key."""
        app = self._config.app(key)
        return self.create_from_config(app)

    def create_from_config(self, app: ApplicationConfig) -> BrowserKioskLauncher:
        """Create one browser launcher from an already resolved app config."""
        if app.type is not ApplicationType.BROWSER:
            raise ValueError(
                f"Application {app.key!r} is {app.type.value}, not browser"
            )
        if not app.enabled:
            raise ValueError(f"Application {app.key!r} is disabled")
        if app.url is None or app.profile is None:
            raise ValueError(
                f"Browser application {app.key!r} requires url and profile"
            )

        profile_path = self._profile_path(app.profile)
        return BrowserKioskLauncher(
            url=app.url,
            profile_path=profile_path,
            window_class=self._window_class(app.key),
            exclusive_group=app.exclusive_group,
            window_manager=self._window_manager,
        )

    def _profile_path(self, profile: str) -> Path:
        return self._config.browser.profile_root / profile

    @staticmethod
    def _window_class(key: str) -> str:
        normalized = "".join(
            character if character.isalnum() else "-"
            for character in key
        ).strip("-")
        return f"openroadcode-{normalized or 'browser'}"
