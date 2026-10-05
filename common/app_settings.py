# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent user-facing settings shared across OpenRoadCode applications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from common.units import UnitSystem
from common.xdg_paths import openroadcode_config_dir


DEFAULT_APP_SETTINGS_PATH = openroadcode_config_dir("settings.toml")


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Contain user preferences that apply across ORC applications."""

    unit_system: UnitSystem = UnitSystem.IMPERIAL
    radar_palette: str = "universal"


class AppSettingsStore:
    """Persist global ORC user preferences in the XDG configuration directory."""

    def __init__(
        self,
        path: str | Path = DEFAULT_APP_SETTINGS_PATH,
        *,
        default: AppSettings = AppSettings(),
    ) -> None:
        self._path = Path(path).expanduser()
        self._default = default

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppSettings:
        """Load settings, returning configured defaults for missing or invalid data."""
        if not self._path.is_file():
            return self._default
        try:
            with self._path.open("rb") as file:
                data = tomllib.load(file)
            display = data.get("display", {})
            weather = data.get("weather", {})
            radar_palette = weather.get("radar_palette", self._default.radar_palette)
            if radar_palette not in ("universal", "classic"):
                raise ValueError("invalid radar palette")
            return AppSettings(
                unit_system=UnitSystem(
                    display.get("unit_system", self._default.unit_system.value)
                ),
                radar_palette=radar_palette,
            )
        except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError):
            return self._default

    def save(self, settings: AppSettings) -> None:
        """Persist the complete global preference state."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            "[display]\n"
            f'unit_system = "{settings.unit_system.value}"\n'
            "\n[weather]\n"
            f'radar_palette = "{settings.radar_palette}"\n',
            encoding="utf-8",
        )
