# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component-level behavior tests for the tiered fuel gauge."""

from frontends.tk.automotive.fuel_level_gauge import FuelLevelGauge


def test_active_segments_are_clamped_and_tiered() -> None:
    assert FuelLevelGauge.active_segment_count(None) == 0
    assert FuelLevelGauge.active_segment_count(-5.0) == 0
    assert FuelLevelGauge.active_segment_count(1.0) == 1
    assert FuelLevelGauge.active_segment_count(25.0) == 3
    assert FuelLevelGauge.active_segment_count(50.0) == 6
    assert FuelLevelGauge.active_segment_count(100.0) == 12
    assert FuelLevelGauge.active_segment_count(150.0) == 12


def test_fuel_level_tiers() -> None:
    assert FuelLevelGauge.level_tier(None) == "unknown"
    assert FuelLevelGauge.level_tier(8.0) == "danger"
    assert FuelLevelGauge.level_tier(12.5) == "danger"
    assert FuelLevelGauge.level_tier(20.0) == "caution"
    assert FuelLevelGauge.level_tier(25.0) == "caution"
    assert FuelLevelGauge.level_tier(25.1) == "normal"
    assert FuelLevelGauge.level_tier(100.0) == "normal"
