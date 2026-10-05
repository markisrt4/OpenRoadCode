# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Protect map command framing when UI and telemetry publish concurrently."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event

from protocols.map_renderer.map_renderer_client import MapRendererClient


class MultipartPublisher:
    def __init__(self):
        self.parts = []
        self.position_started = Event()
        self.release_position = Event()
        self.radar_started = Event()

    def publish(self, topic, payload):
        self.parts.append(topic)
        if payload["command"] == "set_position":
            self.position_started.set()
            assert self.release_position.wait(2)
        else:
            self.radar_started.set()
        self.parts.append(dict(payload))


def test_radar_cannot_interleave_with_position_multipart_message():
    publisher = MultipartPublisher()
    client = MapRendererClient(publisher)
    with ThreadPoolExecutor(max_workers=2) as workers:
        position = workers.submit(client.set_position, 42.8, -83.0)
        assert publisher.position_started.wait(2)
        radar = workers.submit(client.set_weather_radar, None, enabled=False)
        try:
            concurrent_send = publisher.radar_started.wait(0.2)
        finally:
            publisher.release_position.set()
        position.result(timeout=2)
        radar.result(timeout=2)
    assert not concurrent_send
    assert publisher.parts[0] == "map.command"
    assert publisher.parts[1]["command"] == "set_position"
    assert publisher.parts[2] == "map.command"
    assert publisher.parts[3]["command"] == "set_weather_radar"
