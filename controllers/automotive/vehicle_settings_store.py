# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from controllers.automotive.vehicle_configuration import (
    EngineInductionType,
    VehicleConfiguration,
)


DEFAULT_VEHICLE_SETTINGS_PATH = (
    Path.home() / ".config" / "openroadcode" / "vehicle.toml"
)


class VehicleSettingsStore:
    """Persist user-selected vehicle configuration outside the source tree."""

    def __init__(
        self,
        path: str | Path = DEFAULT_VEHICLE_SETTINGS_PATH,
        *,
        default: VehicleConfiguration = VehicleConfiguration(),
    ) -> None:
        self._path = Path(path).expanduser()
        self._default = default

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
            "[engine]\n"
            f'induction = "{configuration.induction.value}"\n',
            encoding="utf-8",
        )
