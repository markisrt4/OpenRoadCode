# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # Python 3.10
    import tomli as tomllib

from ui.automotive.vehicle_configuration import EngineInductionType, VehicleConfiguration

DEFAULT_VEHICLE_SETTINGS_PATH = Path.home() / ".config" / "openroadcode" / "vehicle.toml"


class VehicleSettingsStore:
    """Persist user-selected vehicle configuration outside the source tree."""

    def __init__(
        self,
        path: str | Path = DEFAULT_VEHICLE_SETTINGS_PATH,
        *,
        default: VehicleConfiguration | None = None,
    ) -> None:
        self._path = Path(path).expanduser()
        self._default = default if default is not None else VehicleConfiguration()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> VehicleConfiguration:
        if not self._path.is_file():
            return self._default
        try:
            with self._path.open("rb") as file:
                data = tomllib.load(file)
            engine = data.get("engine", {})
            return VehicleConfiguration(
                induction=EngineInductionType(
                    engine.get("induction", self._default.induction.value)
                )
            )
        except (OSError, ValueError, TypeError, tomllib.TOMLDecodeError):
            return self._default

    def save(self, configuration: VehicleConfiguration) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            f'[engine]\ninduction = "{configuration.induction.value}"\n',
            encoding="utf-8",
        )
