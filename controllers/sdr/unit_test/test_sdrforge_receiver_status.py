# SPDX-License-Identifier: MIT
"""Hardware-free SDRForge receiver telemetry contract tests."""

import json

import pytest

from controllers.sdr.sdrforge_spectrum_subscriber import (
    SdrForgeReceiverStatus,
    decode_receiver_message,
    decode_spectrum_message,
)


def wire(topic: str, payload: dict) -> bytes:
    return (topic + " " + json.dumps({
        "schema_version": 1, "payload": payload,
    })).encode()


@pytest.mark.parametrize("mode, bandwidth", [
    ("WFM", 200_000), ("NFM", 12_500), ("NFM", 7_500),
    ("AM", 6_000), ("AM", 10_000),
])
def test_receiver_mode_and_bandwidth(mode: str, bandwidth: int) -> None:
    message = wire("receiver", {
        "channel_frequency_hz": 104_300_000,
        "mode": mode, "bandwidth_hz": bandwidth, "running": True,
        "rds": None, "stereo_locked": None,
    })
    assert decode_receiver_message(message) == SdrForgeReceiverStatus(
        104_300_000, mode, bandwidth, True,
    )
    assert decode_spectrum_message(message) is None


def test_legacy_receiver_message_is_ignored() -> None:
    assert decode_receiver_message(wire("receiver", {
        "channel_frequency_hz": 104_300_000,
        "stereo_locked": True,
    })) is None


@pytest.mark.parametrize("field, value", [
    ("channel_frequency_hz", -1), ("mode", "SSB"),
    ("bandwidth_hz", 0), ("running", 1),
])
def test_invalid_receiver_metadata_rejected(field: str, value: object) -> None:
    payload = {
        "channel_frequency_hz": 104_300_000, "mode": "NFM",
        "bandwidth_hz": 12_500, "running": True,
    }
    payload[field] = value
    with pytest.raises(ValueError):
        decode_receiver_message(wire("receiver", payload))


def test_spectrum_topic_is_independent() -> None:
    assert decode_receiver_message(wire("spectrum", {
        "timestamp_ns": 1, "center_frequency_hz": 104_300_000,
    })) is None
