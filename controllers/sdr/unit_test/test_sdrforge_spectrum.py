"""SDRForge spectrum contract tests without RF hardware or a display."""

import pytest

from controllers.sdr.sdrforge_spectrum import SdrForgeSpectrumFrame


def snapshot(**overrides):
    payload = {
        "timestamp_ns": 123,
        "center_frequency_hz": 104_300_000,
        "sample_rate_hz": 2_400_000,
        "bin_count": 4,
        "first_bin_frequency_hz": 103_100_000.0,
        "bin_spacing_hz": 600_000.0,
        "power_db": [-40.0, None, -15.0, -30.0],
    }
    payload.update(overrides)
    return payload


def test_absolute_frequency_and_missing_bins():
    frame = SdrForgeSpectrumFrame.from_payload(snapshot())
    assert frame.frequency_hz(0) == 103_100_000
    assert frame.frequency_hz(2) == 104_300_000
    assert frame.power_db == (-40.0, None, -15.0, -30.0)


def test_retune_updates_absolute_frequency():
    frame = SdrForgeSpectrumFrame.from_payload(snapshot(
        center_frequency_hz=162_550_000,
        first_bin_frequency_hz=161_350_000.0,
    ))
    assert frame.frequency_hz(2) == 162_550_000


@pytest.mark.parametrize("changes", [
    {"bin_count": 3},
    {"power_db": [-40, float("nan"), -15, -30]},
    {"bin_spacing_hz": 1.0},
    {"sample_rate_hz": 0},
    {"center_frequency_hz": True},
])
def test_invalid_snapshot_rejected(changes):
    with pytest.raises((ValueError, TypeError)):
        SdrForgeSpectrumFrame.from_payload(snapshot(**changes))
