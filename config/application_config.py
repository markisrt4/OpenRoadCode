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
    BROWSER = "browser"
    ADSB = "adsb"
    NATIVE = "native"


class AdsbDataSource(str, Enum):
    RTLSDR = "rtlsdr"
    SIMULATION = "simulation"


class StartupPolicy(str, Enum):
    LAZY = "lazy"
    PRELOAD = "preload"
    PERSISTENT = "persistent"


class PresentationTargetType(str, Enum):
    """Describe how an application presentation target is reached."""

    X11 = "x11"


@dataclass(frozen=True, slots=True)
class PresentationTargetConfig:
    """Configure one named destination for application presentation."""

    key: str
    type: PresentationTargetType
    display: str


@dataclass(frozen=True, slots=True)
class BrowserConfig:
    profile_root: Path = Path.home() / ".local" / "share" / "openroadcode" / "browser"


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    key: str
    type: ApplicationType
    enabled: bool = True
    startup: StartupPolicy = StartupPolicy.LAZY
    url: str | None = None
    profile: str | None = None
    exclusive_group: str | None = None
    target: str | None = None
    adsb_data_source: AdsbDataSource | None = None


@dataclass(frozen=True, slots=True)
class ApplicationsConfig:
    browser: BrowserConfig
    apps: tuple[ApplicationConfig, ...]
    presentation_targets: tuple[PresentationTargetConfig, ...] = ()
    default_target: str | None = None

    def app(self, key: str) -> ApplicationConfig:
        for app in self.apps:
            if app.key == key:
                return app
        raise KeyError(f"Unknown application: {key}")

    def target(self, key: str) -> PresentationTargetConfig:
        for target in self.presentation_targets:
            if target.key == key:
                return target
        raise KeyError(f"Unknown presentation target: {key}")

    def target_for_app(self, app: ApplicationConfig) -> PresentationTargetConfig | None:
        key = app.target or self.default_target
        if key is None:
            return None
        return self.target(key)

    def enabled_apps(self) -> tuple[ApplicationConfig, ...]:
        return tuple(app for app in self.apps if app.enabled)

    def preload_apps(self) -> tuple[ApplicationConfig, ...]:
        return tuple(app for app in self.apps if app.enabled and app.startup is StartupPolicy.PRELOAD)


class ApplicationsConfigParser:
    def __init__(self, config_path: str | Path) -> None:
        self.config_path = Path(config_path).expanduser().resolve()

    def load(self) -> ApplicationsConfig:
        try:
            with self.config_path.open("rb") as file:
                data = tomllib.load(file)
        except FileNotFoundError as exc:
            raise ApplicationConfigError(f"Application config file not found: {self.config_path}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ApplicationConfigError(f"Invalid TOML in {self.config_path}: {exc}") from exc

        root = self._expect_table(data, "root")
        browser = self._parse_browser(root.get("browser", {}))
        targets, default_target = self._parse_presentation(root.get("presentation", {}))
        apps = self._parse_apps(root.get("apps", {}))
        target_keys = {target.key for target in targets}
        if default_target is not None and default_target not in target_keys:
            raise ApplicationConfigError(f"presentation.default_target references unknown target {default_target!r}")
        for app in apps:
            if app.target is not None and app.target not in target_keys:
                raise ApplicationConfigError(f"apps.{app.key}.target references unknown presentation target {app.target!r}")
        return ApplicationsConfig(browser=browser, apps=apps, presentation_targets=targets, default_target=default_target)

    def _parse_browser(self, data: Any) -> BrowserConfig:
        section = self._expect_table(data, "browser")
        raw_root = section.get("profile_root", "~/.local/share/openroadcode/browser")
        if not isinstance(raw_root, str) or not raw_root.strip():
            raise ApplicationConfigError("browser.profile_root must be a non-empty string")
        return BrowserConfig(profile_root=Path(raw_root).expanduser())

    def _parse_presentation(self, data: Any) -> tuple[tuple[PresentationTargetConfig, ...], str | None]:
        section = self._expect_table(data, "presentation")
        default_target = self._optional_string(section, "default_target", "presentation.default_target")
        raw_targets = self._expect_table(section.get("targets", {}), "presentation.targets")
        targets: list[PresentationTargetConfig] = []
        for key, raw_target in raw_targets.items():
            target = self._expect_table(raw_target, f"presentation.targets.{key}")
            target_type = self._enum_value(PresentationTargetType, target.get("type"), f"presentation.targets.{key}.type")
            display = self._optional_string(target, "display", f"presentation.targets.{key}.display")
            if target_type is PresentationTargetType.X11 and display is None:
                raise ApplicationConfigError(f"presentation.targets.{key}.display is required for x11 targets")
            targets.append(PresentationTargetConfig(key=key, type=target_type, display=display or ""))
        return tuple(targets), default_target

    def _parse_apps(self, data: Any) -> tuple[ApplicationConfig, ...]:
        section = self._expect_table(data, "apps")
        apps: list[ApplicationConfig] = []
        for key, raw_app in section.items():
            app = self._expect_table(raw_app, f"apps.{key}")
            app_type = self._enum_value(ApplicationType, app.get("type"), f"apps.{key}.type")
            startup = self._enum_value(StartupPolicy, app.get("startup", StartupPolicy.LAZY.value), f"apps.{key}.startup")
            enabled = app.get("enabled", True)
            if not isinstance(enabled, bool):
                raise ApplicationConfigError(f"apps.{key}.enabled must be a boolean")
            url = self._optional_string(app, "url", f"apps.{key}.url")
            profile = self._optional_string(app, "profile", f"apps.{key}.profile")
            exclusive_group = self._optional_string(app, "exclusive_group", f"apps.{key}.exclusive_group")
            target = self._optional_string(app, "target", f"apps.{key}.target")
            adsb_data_source = None
            if app_type is ApplicationType.ADSB:
                data_config = self._expect_table(app.get("data", {}), f"apps.{key}.data")
                adsb_data_source = self._enum_value(AdsbDataSource, data_config.get("source", AdsbDataSource.RTLSDR.value), f"apps.{key}.data.source")
            if app_type in (ApplicationType.BROWSER, ApplicationType.ADSB) and url is None:
                raise ApplicationConfigError(f"apps.{key}.url is required for {app_type.value} applications")
            if app_type is ApplicationType.BROWSER and profile is None:
                raise ApplicationConfigError(f"apps.{key}.profile is required for browser applications")
            apps.append(ApplicationConfig(key=key, type=app_type, enabled=enabled, startup=startup, url=url, profile=profile, exclusive_group=exclusive_group, target=target, adsb_data_source=adsb_data_source))
        return tuple(apps)

    @staticmethod
    def _expect_table(data: Any, name: str) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise ApplicationConfigError(f"{name} must be a TOML table")
        return data

    @staticmethod
    def _optional_string(section: dict[str, Any], key: str, name: str) -> str | None:
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
            raise ApplicationConfigError(f"{name} must be one of: {choices}") from exc
