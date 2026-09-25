# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tests for layered TOML runtime configuration."""

from pathlib import Path

import pytest

from config.toml_overlay import TomlOverlayError, load_toml_layers, merge_toml_tables


def test_nested_tables_merge_without_erasing_siblings() -> None:
    base = {
        "messaging": {"publisher_endpoint": "base-pub", "subscriber_endpoint": "base-sub"},
        "services": {
            "navigation": {
                "rate_hz": 10.0,
                "inputs": {
                    "gps": {"source": "device", "device": "gpsd"},
                    "imu": {"source": "device", "device": "mpu6050"},
                },
            }
        },
    }
    profile = {
        "services": {
            "navigation": {
                "inputs": {
                    "gps": {"source": "simulation"},
                }
            }
        }
    }

    merged = merge_toml_tables(base, profile)

    assert merged["messaging"]["publisher_endpoint"] == "base-pub"
    assert merged["services"]["navigation"]["rate_hz"] == 10.0
    assert merged["services"]["navigation"]["inputs"]["gps"] == {
        "source": "simulation",
        "device": "gpsd",
    }
    assert merged["services"]["navigation"]["inputs"]["imu"]["device"] == "mpu6050"


def test_later_layers_override_platform_then_profile(tmp_path: Path) -> None:
    base = tmp_path / "base.toml"
    platform = tmp_path / "platform.toml"
    profile = tmp_path / "profile.toml"

    base.write_text(
        """
[messaging]
publisher_endpoint = "base"

[services.navigation]
rate_hz = 10.0

[services.navigation.inputs.gps]
source = "device"
device = "gpsd"
""",
        encoding="utf-8",
    )
    platform.write_text(
        """
[messaging]
publisher_endpoint = "platform"

[services.navigation]
rate_hz = 20.0
""",
        encoding="utf-8",
    )
    profile.write_text(
        """
[services.navigation.inputs.gps]
source = "simulation"
""",
        encoding="utf-8",
    )

    merged = load_toml_layers(base, platform, profile)

    assert merged["messaging"]["publisher_endpoint"] == "platform"
    assert merged["services"]["navigation"]["rate_hz"] == 20.0
    assert merged["services"]["navigation"]["inputs"]["gps"]["source"] == "simulation"
    assert merged["services"]["navigation"]["inputs"]["gps"]["device"] == "gpsd"


def test_arrays_replace_instead_of_merging() -> None:
    merged = merge_toml_tables(
        {"radios": [{"key": "fm"}, {"key": "airband"}]},
        {"radios": [{"key": "weather"}]},
    )

    assert merged["radios"] == [{"key": "weather"}]


def test_merge_does_not_mutate_inputs() -> None:
    base = {"services": {"navigation": {"rate_hz": 10.0}}}
    override = {"services": {"navigation": {"rate_hz": 20.0}}}

    merged = merge_toml_tables(base, override)

    assert merged["services"]["navigation"]["rate_hz"] == 20.0
    assert base["services"]["navigation"]["rate_hz"] == 10.0
    assert override["services"]["navigation"]["rate_hz"] == 20.0


def test_missing_layer_reports_the_specific_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.toml"

    with pytest.raises(TomlOverlayError, match="configuration file not found"):
        load_toml_layers(missing)
