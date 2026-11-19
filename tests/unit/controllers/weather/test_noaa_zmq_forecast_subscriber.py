# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Hardware-free subscriber lifecycle and transport tests."""

from __future__ import annotations

import json
import queue
import sys
import time
from types import SimpleNamespace

import pytest

from controllers.weather.noaa_forecast_store import NoaaForecastStore
from controllers.weather.noaa_weather_event_adapter import NoaaWeatherEventAdapter
from controllers.weather.noaa_zmq_forecast_subscriber import NoaaZmqForecastSubscriber


class FakeSocket:
    def __init__(self):
        self.frames = queue.Queue()
        self.options = []
        self.endpoint = None
        self.closed = False

    def setsockopt(self, option, value):
        self.options.append((option, value))

    def connect(self, endpoint):
        self.endpoint = endpoint

    def recv(self):
        return self.frames.get_nowait()

    def close(self, *, linger):
        self.closed = True


class FakeContext:
    def __init__(self):
        self.sockets = []

    def socket(self, _kind):
        socket = FakeSocket()
        self.sockets.append(socket)
        return socket


class FakePoller:
    def __init__(self):
        self.socket = None

    def register(self, socket, _kind):
        self.socket = socket

    def poll(self, timeout):
        try:
            self.socket.frames.queue[0]
        except IndexError:
            time.sleep(timeout / 1000)
            return []
        return [(self.socket, 1)]


def install_fake_zmq(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "zmq",
        SimpleNamespace(
            SUB=1,
            SUBSCRIBE=2,
            LINGER=3,
            POLLIN=4,
            ZMQError=OSError,
            Poller=FakePoller,
        ),
    )


def forecast_frame():
    payload = {
        "event": "noaa_forecast_completed",
        "forecast_area": None,
        "forecast_areas": [],
        "forecast_cycle": 1,
        "forecast_revision": 1,
        "completed_forecast": {
            "forecast": {"period": "tonight", "conditions": "cloudy"}
        },
    }
    return b"noaa.forecast " + json.dumps(
        {"schema_version": 1, "payload": payload}
    ).encode()


def wait_until(predicate, *, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    pytest.fail("subscriber did not reach expected state")


def test_start_stop_restart_and_idempotent_start(monkeypatch):
    install_fake_zmq(monkeypatch)
    context = FakeContext()
    store = NoaaForecastStore()
    subscriber = NoaaZmqForecastSubscriber(
        NoaaWeatherEventAdapter(store),
        context_factory=lambda: context,
        poll_timeout_ms=5,
    )
    subscriber.start()
    subscriber.start()
    wait_until(lambda: len(context.sockets) == 1)
    assert subscriber.running
    assert context.sockets[0].endpoint == "tcp://127.0.0.1:5573"
    subscriber.stop()
    assert context.sockets[0].closed
    assert not subscriber.running
    subscriber.stop()

    subscriber.start()
    wait_until(lambda: len(context.sockets) == 2)
    assert subscriber.running
    subscriber.stop()
    assert context.sockets[1].closed


def test_valid_and_invalid_frames_do_not_kill_worker(monkeypatch):
    install_fake_zmq(monkeypatch)
    context = FakeContext()
    store = NoaaForecastStore()
    subscriber = NoaaZmqForecastSubscriber(
        NoaaWeatherEventAdapter(store),
        context_factory=lambda: context,
        poll_timeout_ms=5,
    )
    subscriber.start()
    try:
        wait_until(lambda: bool(context.sockets))
        context.sockets[0].frames.put(b"noaa.forecast not-json")
        context.sockets[0].frames.put(forecast_frame())
        wait_until(lambda: subscriber.rejected == 1 and subscriber.received == 1)
        assert subscriber.running
        assert store.latest().period == "tonight"
    finally:
        subscriber.stop()


def test_rejects_nonpositive_poll_timeout():
    with pytest.raises(ValueError, match="poll_timeout_ms"):
        NoaaZmqForecastSubscriber(
            NoaaWeatherEventAdapter(NoaaForecastStore()),
            poll_timeout_ms=0,
        )
