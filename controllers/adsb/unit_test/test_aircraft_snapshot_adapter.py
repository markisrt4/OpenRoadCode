"""SDRForge-compatible snapshots at the ORC boundary."""
from dataclasses import dataclass
from math import degrees
import pytest
from controllers.adsb.aircraft_snapshot_adapter import aircraft_from_snapshot


@dataclass(frozen=True)
class Track:
    icao: str = "ABCDEF"
    latitude: float = 42.5
    longitude: float = -83.0
    altitude_ft: int = 10000
    heading_deg: float = 90
    speed_kt: float = 200
    vertical_rate_fpm: int = 600
    callsign: str = "TEST"
    last_seen: float = 3.0


def test_tracker_dataclass_conversion():
    aircraft = aircraft_from_snapshot([Track()])[0]
    assert degrees(aircraft.position.latitude_rad) == pytest.approx(42.5)
    assert aircraft.position.altitude_m == pytest.approx(3048)
    assert aircraft.speed_m_s == pytest.approx(200 * 1852 / 3600)
    assert aircraft.vertical_speed_m_s == pytest.approx(600 * 0.3048 / 60)


def test_unknown_position():
    aircraft = aircraft_from_snapshot([{"icao": "ABCDEF", "latitude": None, "longitude": None}])[0]
    assert aircraft.position is None
