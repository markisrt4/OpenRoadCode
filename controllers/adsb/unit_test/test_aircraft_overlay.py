"""Aircraft overlay data contract tests."""

from controllers.adsb.aircraft_overlay import aircraft_geojson


def test_geojson_coordinates_and_heading():
    data = aircraft_geojson(
        [
            {
                "icao": "a1b2c3",
                "latitude": 42.3,
                "longitude": -83.1,
                "callsign": "TEST123",
                "heading_deg": 275,
                "altitude_ft": 12000,
            }
        ]
    )
    assert len(data["features"]) == 1
    feature = data["features"][0]
    assert feature["geometry"]["coordinates"] == [-83.1, 42.3]
    assert feature["properties"]["heading_deg"] == 275
    assert feature["properties"]["icao"] == "A1B2C3"


def test_omits_unknown_or_invalid_positions():
    data = aircraft_geojson(
        [
            {"icao": "111111", "latitude": None, "longitude": -83},
            {"icao": "222222", "latitude": 95, "longitude": 0},
            {"icao": "333333", "latitude": float("nan"), "longitude": 0},
            {"icao": "444444", "latitude": 42, "longitude": -83},
        ]
    )
    assert [f["id"] for f in data["features"]] == ["444444"]


def test_empty_snapshot_clears_overlay():
    assert aircraft_geojson([]) == {"type": "FeatureCollection", "features": []}
