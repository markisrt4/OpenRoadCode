# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.automotive import EngineInductionType, VehicleConfiguration
from controllers.automotive.vehicle_settings_store import VehicleSettingsStore


def test_vehicle_settings_store_uses_default_when_missing(tmp_path) -> None:
    default = VehicleConfiguration(induction=EngineInductionType.TURBOCHARGED)
    store = VehicleSettingsStore(tmp_path / "vehicle.toml", default=default)

    assert store.load() == default


def test_vehicle_settings_store_round_trip(tmp_path) -> None:
    path = tmp_path / "vehicle.toml"
    store = VehicleSettingsStore(path)

    expected = VehicleConfiguration(
        induction=EngineInductionType.SUPERCHARGED
    )
    store.save(expected)

    assert store.load() == expected
    assert 'induction = "supercharged"' in path.read_text(encoding="utf-8")


def test_vehicle_settings_store_falls_back_on_invalid_value(tmp_path) -> None:
    path = tmp_path / "vehicle.toml"
    path.write_text('[engine]\ninduction = "rocket"\n', encoding="utf-8")
    default = VehicleConfiguration(
        induction=EngineInductionType.NATURALLY_ASPIRATED
    )

    assert VehicleSettingsStore(path, default=default).load() == default
