# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Parse user-facing application lifecycle and presentation configuration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


class ApplicationConfigError(ValueError):
    """Raised when the application configuration is missing or invalid."""


class ApplicationType(str, Enum):
    """Describe how an application is launched."""

    BROWSER = "browser"
    ADSB = "adsb"
    NATIVE = "native"


class StartupPolicy(str, Enum):
    """Describe when an application should be started."""

    LAZY = "lazy"
    PRELOAD = "preload"
    PERSISTENT = "persistent"


@dataclass(frozen=True, slots=True)
class BrowserConfig:
    """Configure shared browser application storage."""

    profile_root: Path = Path.home() / ".local" / "share" / "openroadcode" / "browser"


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    """Configure one user-facing application."""

    key: str
    type: ApplicationType
    enabled: bool = True
    startup: StartupPolicy = StartupPolicy.LAZY
    url: str | None = None
    profile: str | None = None
    exclusive_group: str | None = None


@dataclass(frozen=True, slots=True)
class ApplicationsConfig:
    """Contain browser defaults and configured user-facing applications."""

    browser: BrowserConfig
    apps: tuple[ApplicationConfig, ...]

    def app(self, key: str) -> ApplicationConfig:
        """Return one configured application by stable identifier."""
        for app in self.apps:
            if app.key == key:
                return app
        raise KeyError(f"Unknown application: {key}")

    def enabled_apps(self) -> tuple[ApplicationConfig, ...]:
        """Return applications enabled in this configuration."""
        return tuple(app for app in self.apps if app.enabled)

    def preload_apps(self) -> tuple[ApplicationConfig, ...]:
        """Return enabled applications configured for background preload."""
        return tuple(
            app
            for app in self.apps
            if app.enabled and app.startup is StartupPolicy.PRELOAD
        )


class ApplicationsConfigParser:
    """Parse application lifecycle and presentation policy from TOML."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).expanduser().resolve()

    def load(self) -> ApplicationsConfig:
        """Load and validate the configured TOML file."""
        try:
            with self.config_path.open("rb") as file:
                data = tomllib.load(file)
        except FileNotFoundError as exc:
            raise ApplicationConfigError(
                f"Application config file not found: {self.config_path}"
            ) from exc
        except tomllib.TOMLDecodeError as exc:
            raise ApplicationConfigError(
                f"Invalid TOML in {self.config_path}: {exc}"
            ) from exc

        root = self._expect_table(data, "root")
        browser = self._parse_browser(root.get("browser", {}))
        apps = self._parse_apps(root.get("apps", {}))
        return ApplicationsConfig(browser=browser, apps=apps)

    def _parse_browser(self, data: Any) -> BrowserConfig:
        section = self._expect_table(data, "browser")
        raw_root = section.get(
            "profile_root",
            "~/.local/share/openroadcode/browser",
        )
        if not isinstance(raw_root, str) or not raw_root.strip():
            raise ApplicationConfigError(
                "browser.profile_root must be a non-empty string"
            )
        return BrowserConfig(profile_root=Path(raw_root).expanduser())

    def _parse_apps(self, data: Any) -> tuple[ApplicationConfig, ...]:
        section = self._expect_table(data, "apps")
        apps: list[ApplicationConfig] = []
        for key, raw_app in section.items():
            if not isinstance(key, str) or not key:
                raise ApplicationConfigError("Application keys must be non-empty strings")
            app = self._expect_table(raw_app, f"apps.{key}")
            app_type = self._enum_value(
                ApplicationType,
                app.get("type"),
                f"apps.{key}.type",
            )
            startup = self._enum_value(
                StartupPolicy,
                app.get("startup", StartupPolicy.LAZY.value),
                f"apps.{key}.startup",
            )
            enabled = app.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ApplicationConfigError(f"apps.{key}.enabled must be a boolean")

            url = self._optional_string(app, "url", f"apps.{key}.url")
            profile = self._optional_string(app, "profile", f"apps.{key}.profile")
            exclusive_group = self._optional_string(
                app,
                "exclusive_group",
                f"apps.{key}.exclusive_group",
            )

            if app_type in (ApplicationType.BROWSER, ApplicationType.ADSB) and url is None:
                raise ApplicationConfigError(
                    f"apps.{key}.url is required for {app_type.value} applications"
                )
            if app_type is ApplicationType.BROWSER and profile is None:
                raise ApplicationConfigError(
                    f"apps.{key}.profile is required for browser applications"
                )

            apps.append(
                ApplicationConfig(
                    key=key,
                    type=app_type,
                    enabled=enabled,
                    startup=startup,
                    url=url,
                    profile=profile,
                    exclusive_group=exclusive_group,
                )
            )
        return tuple(apps)

    @staticmethod
    def _expect_table(data: Any, name: str) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ApplicationConfigError(f"{name} must be a TOML table")
        return data

    @staticmethod
    def _optional_string(
        section: dict[str, Any],
        key: str,
        name: str,
    ) -> str | None:
        value = section.get(key)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ApplicationConfigError(f"{name} must be a non-empty string")
        return value

    @staticmethod
    def _enum_value(enum_type, value: Any, name: str):
        if not isinstance(value, str):
            raise ApplicationConfigError(f"{name} must be a string")
        try:
            return enum_type(value)
        except ValueError as exc:
            choices = ", ".join(member.value for member in enum_type)
            raise ApplicationConfigError(
                f"{name} must be one of: {choices}"
            ) from exc
