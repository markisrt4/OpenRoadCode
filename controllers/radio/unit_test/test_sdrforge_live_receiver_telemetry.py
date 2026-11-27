# SPDX-License-Identifier: MIT
"""Verify SDRForge's live receiver status reaches the ORC radio contract."""

from controllers.radio.adapters.sdrforge_zmq_spectrum_adapter import receiver_telemetry


def test_live_mode_and_bandwidth_are_exposed() -> None:
    payload = {
        "channel_frequency_hz": 162_550_000,
        "mode": "NFM",
        "bandwidth_hz": 12_500,
        "running": True,
        "stereo_locked": None,
        "rds": None,
    }
    telemetry = receiver_telemetry("receiver", payload)
    assert telemetry is not None
    assert telemetry.frequency_hz == 162_550_000
    assert telemetry.mode == "NFM"
    assert telemetry.bandwidth_hz == 12_500
    assert telemetry.receiver_running is True
    assert telemetry.stereo_locked is None


def test_legacy_wfm_receiver_remains_compatible() -> None:
    telemetry = receiver_telemetry(
        "receiver",
        {
            "channel_frequency_hz": 104_300_000,
            "stereo_locked": True,
            "rds": None,
        },
    )
    assert telemetry is not None
    assert telemetry.mode is None
    assert telemetry.bandwidth_hz is None
    assert telemetry.receiver_running is None
    assert telemetry.stereo_locked is True


def test_invalid_live_receiver_mode_is_rejected() -> None:
    assert (
        receiver_telemetry(
            "receiver",
            {
                "channel_frequency_hz": 104_300_000,
                "mode": "SSB",
                "bandwidth_hz": 12_500,
                "running": True,
            },
        )
        is None
    )
