# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Regression coverage for radar and POI commands sharing one map client."""

from unittest.mock import Mock

from protocols.map_renderer.map_renderer_client import MapRendererClient
from protocols.map_renderer.map_renderer_protocol import MAP_RENDERER_COMMAND_TOPIC


def test_radar_and_poi_commands_share_client_without_losing_payloads():
    publisher = Mock()
    client = MapRendererClient(publisher)
    pois = {"type": "FeatureCollection", "features": []}
    client.set_weather_radar("https://example.com/{z}/{x}/{y}.png", frame_time=123)
    client.set_poi_results(pois)
    client.pan_screen(20, 30)
    client.set_weather_radar(None, enabled=False)
    payloads = [call.args[1] for call in publisher.publish.call_args_list]
    assert all(call.args[0] == MAP_RENDERER_COMMAND_TOPIC
               for call in publisher.publish.call_args_list)
    assert [payload["command"] for payload in payloads] == [
        "set_weather_radar", "set_poi_results", "pan_screen", "set_weather_radar"
    ]
    assert payloads[0]["frame_time"] == 123
    assert payloads[1]["geojson"] == pois
    assert payloads[2]["right_px"] == 20
    assert payloads[3]["enabled"] is False
    client.close()
