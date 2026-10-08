# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for persistent application settings."""

from common.app_settings import AppSettings, AppSettingsStore
from common.units import UnitSystem


def test_missing_settings_use_default(tmp_path) -> None:
    default = AppSettings(unit_system=UnitSystem.METRIC)
    store = AppSettingsStore(tmp_path / "settings.toml", default=default)

    assert store.load() == default


def test_settings_round_trip(tmp_path) -> None:
    store = AppSettingsStore(tmp_path / "settings.toml")
    settings = AppSettings(unit_system=UnitSystem.METRIC, radar_palette="classic")

    store.save(settings)

    assert store.load() == settings
    contents = store.path.read_text(encoding="utf-8")
    assert 'unit_system = "metric"' in contents
    assert 'radar_palette = "classic"' in contents


def test_invalid_unit_system_uses_default(tmp_path) -> None:
    path = tmp_path / "settings.toml"
    path.write_text('[display]\nunit_system = "furlongs"\n', encoding="utf-8")
    default = AppSettings(unit_system=UnitSystem.IMPERIAL)

    assert AppSettingsStore(path, default=default).load() == default


def test_invalid_radar_palette_uses_default(tmp_path) -> None:
    path = tmp_path / "settings.toml"
    path.write_text(
        '[display]\nunit_system = "imperial"\n\n[weather]\nradar_palette = "infrared"\n',
        encoding="utf-8",
    )

    assert AppSettingsStore(path).load() == AppSettings()
