"""Native aircraft map command contract."""
from controllers.adsb.aircraft_overlay import aircraft_geojson
from protocols.map_renderer.map_renderer_client import MapRendererClient
from protocols.map_renderer.map_renderer_protocol import MapRendererCommand


class RecordingPublisher:
    def __init__(self):
        self.messages = []

    def publish(self, topic, payload):
        self.messages.append((topic, payload))


def test_aircraft_command_uses_dedicated_map_layer():
    publisher = RecordingPublisher()
    client = MapRendererClient(publisher=publisher)
    features = aircraft_geojson([{
        "icao": "a1b2c3", "latitude": 42.3, "longitude": -83.1,
        "heading_deg": 90, "callsign": "TEST123",
    }])
    client.set_aircraft(features)
    topic, message = publisher.messages[-1]
    assert topic == "map.command"
    assert message["command"] == MapRendererCommand.SET_AIRCRAFT
    assert message["geojson"] == features


def test_empty_snapshot_publishes_clear():
    publisher = RecordingPublisher()
    MapRendererClient(publisher=publisher).set_aircraft(aircraft_geojson([]))
    assert publisher.messages[-1][1]["geojson"]["features"] == []
