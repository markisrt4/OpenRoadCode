# SPDX-License-Identifier: MIT
"""Persistent appointment arrival preference regression tests."""

from dataclasses import replace

import pytest

from common.app_settings import AppSettings, AppSettingsStore


def test_arrival_buffer_round_trip(tmp_path):
    store = AppSettingsStore(tmp_path / "settings.toml")
    assert store.load().appointment_arrival_minutes == 10
    settings = replace(store.load(), appointment_arrival_minutes=25)
    store.save(settings)
    assert store.load() == settings
    store.save(replace(store.load(), radar_palette="classic"))
    assert store.load().appointment_arrival_minutes == 25


@pytest.mark.parametrize("value", ["-1", "121", "true", "1.5", '"invalid"'])
def test_invalid_arrival_buffer_preserves_other_settings(tmp_path, value):
    store = AppSettingsStore(tmp_path / "settings.toml")
    store.path.write_text(
        '[weather]\nradar_palette = "classic"\n[navigation]\n'
        f"appointment_arrival_minutes = {value}\n",
        encoding="utf-8",
    )
    assert store.load() == AppSettings(radar_palette="classic")
