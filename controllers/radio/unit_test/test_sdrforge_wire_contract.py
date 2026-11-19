# SPDX-License-Identifier: MIT
"""SDRForge native wire payloads consumed by ORC, without SDR hardware."""
from controllers.radio.adapters.sdrforge_zmq_spectrum_adapter import (
    receiver_telemetry,
    spectrum_bins,
)


def test_native_receiver_running_and_stopped_payloads():
    base = {
        "channel_frequency_hz": 104_300_000,
        "mode": "WFM",
        "bandwidth_hz": 200_000,
        "stereo_locked": True,
        "rds": None,
    }
    running = receiver_telemetry("receiver", {**base, "running": True})
    stopped = receiver_telemetry("receiver", {**base, "running": False})
    assert running is not None and running.receiver_running is True
    assert stopped is not None and stopped.receiver_running is False
    assert running.frequency_hz == 104_300_000


def test_native_spectrum_accepts_json_null_for_nonfinite_fft_bin():
    payload = {
        "center_frequency_hz": 104_300_000,
        "sample_rate_hz": 2_400_000,
        "bin_count": 3,
        "power_db": [-80.0, None, -35.0],
    }
    bins = spectrum_bins("spectrum", payload)
    assert bins is not None
    assert len(bins) == 3
    assert bins[0] == bins[1] == 0.0
    assert bins[2] == 1.0
