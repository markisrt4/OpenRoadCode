"""Hardware-independent aircraft presentation tests."""

from dataclasses import FrozenInstanceError
from math import radians

import pytest

from frontends.common.map_aircraft_overlay_ui import MapAircraftOverlayUi
from ui.adsb.aircraft_overlay_state import AircraftOverlayState, AircraftPoint
from ui.navigation.map_ui_if import GeoPoint


class Recorder:
    def __init__(self):
        self.snapshots = []

    def set_aircraft(self, geojson):
        self.snapshots.append(geojson)


def test_si_aircraft_snapshot_converts_at_map_boundary():
    renderer = Recorder()
    view = MapAircraftOverlayUi(renderer)
    aircraft = AircraftPoint(
        "a1b2c3",
        GeoPoint(radians(42), radians(-83), 3048),
        callsign="TEST1",
        speed_m_s=100,
        heading_rad=radians(90),
        vertical_speed_m_s=5,
    )
    view.set_aircraft_overlay_state(AircraftOverlayState(enabled=True, aircraft=(aircraft,)))
    feature = renderer.snapshots[-1]["features"][0]
    assert feature["geometry"]["coordinates"] == pytest.approx([-83, 42])
    assert feature["properties"]["heading_deg"] == pytest.approx(90)
    assert feature["properties"]["altitude_ft"] == pytest.approx(10000)
    assert feature["properties"]["speed_kt"] == pytest.approx(194.384, rel=0.001)


def test_hidden_and_empty_snapshots_clear_map():
    renderer = Recorder()
    view = MapAircraftOverlayUi(renderer)
    aircraft = AircraftPoint("abcdef", GeoPoint(0, 0))
    view.set_aircraft_overlay_state(AircraftOverlayState(enabled=False, aircraft=(aircraft,)))
    view.set_aircraft_overlay_state(AircraftOverlayState(enabled=True))
    assert all(not snap["features"] for snap in renderer.snapshots)


def test_immutable_state():
    state = AircraftOverlayState()
    with pytest.raises(FrozenInstanceError):
        state.enabled = True
