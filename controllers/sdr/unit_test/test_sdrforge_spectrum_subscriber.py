# SPDX-License-Identifier: MIT
"""Hardware-independent SDRForge ZMQ spectrum subscriber contract tests."""
from __future__ import annotations

import json
import queue
import time

import pytest

from controllers.sdr.sdrforge_spectrum_subscriber import (
    SdrForgeSpectrumSubscriber,
    decode_receiver_message,
    decode_spectrum_message,
)


def _message(topic: str, payload: dict) -> bytes:
    return topic.encode() + b" " + json.dumps(
        {"schema_version": 1, "payload": payload}
    ).encode()


def _spectrum(timestamp: int, center: int = 104_300_000) -> bytes:
    return _message("spectrum", {
        "timestamp_ns": timestamp,
        "center_frequency_hz": center,
        "sample_rate_hz": 2_400_000,
        "bin_count": 4,
        "first_bin_frequency_hz": center - 1_200_000.0,
        "bin_spacing_hz": 600_000.0,
        "power_db": [-50.0, -30.0, -15.0, -40.0],
    })


class FakeSocket:
    """Queue-backed SUB socket with bounded receive waits."""

    def __init__(self) -> None:
        self.messages: queue.Queue[bytes] = queue.Queue()
        self.closed = False

    def recv(self) -> bytes:
        try:
            return self.messages.get(timeout=0.01)
        except queue.Empty as exc:
            raise TimeoutError from exc

    def close(self) -> None:
        self.closed = True


def test_decode_topics_and_reject_invalid_envelope():
    assert decode_spectrum_message(b"other {}") is None
    assert decode_receiver_message(_spectrum(1)) is None
    frame = decode_spectrum_message(_spectrum(2))
    assert frame is not None
    assert frame.frequency_hz(2) == 104_300_000
    with pytest.raises(ValueError, match="unsupported"):
        decode_spectrum_message(b'spectrum {"schema_version":2,"payload":{}}')


def test_subscriber_retune_resets_waterfall_and_stops():
    socket = FakeSocket()
    subscriber = SdrForgeSpectrumSubscriber(max_rows=3, socket_factory=lambda: socket)
    subscriber.start()
    try:
        socket.messages.put(_spectrum(1))
        socket.messages.put(_spectrum(2))
        deadline = time.monotonic() + 2
        while len(subscriber.snapshot()) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(subscriber.snapshot()) == 2
        socket.messages.put(_spectrum(3, center=101_100_000))
        deadline = time.monotonic() + 2
        while (subscriber.snapshot()[-1].center_frequency_hz != 101_100_000
               and time.monotonic() < deadline):
            time.sleep(0.01)
        rows = subscriber.snapshot()
        assert len(rows) == 1
        assert rows[0].center_frequency_hz == 101_100_000
    finally:
        subscriber.stop()
    assert socket.closed


def test_receiver_status_message():
    status = decode_receiver_message(_message("receiver", {
        "channel_frequency_hz": 104_300_000,
        "mode": "WFM",
        "bandwidth_hz": 200_000,
        "running": True,
    }))
    assert status is not None
    assert status.running
    assert status.frequency_hz == 104_300_000
