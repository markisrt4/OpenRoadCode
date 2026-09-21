# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from tools.map_builder.builder.poi_index import _classification, _transit_mode


def test_bus_stop_normalizes_to_bus() -> None:
    tags = {"highway": "bus_stop", "public_transport": "platform"}
    assert _transit_mode(tags) == "bus"
    assert _classification(tags) == ("transit", "bus", "bus_stop", "bus")


def test_public_transport_station_preserves_rail_mode() -> None:
    tags = {"public_transport": "station", "railway": "station"}
    assert _transit_mode(tags) == "rail"
    assert _classification(tags) == (
        "transit",
        "public_transport",
        "station",
        "rail",
    )


def test_public_transport_stop_position_preserves_tram_mode() -> None:
    tags = {"public_transport": "stop_position", "tram": "yes"}
    assert _transit_mode(tags) == "tram"
    assert _classification(tags) == (
        "transit",
        "public_transport",
        "stop_position",
        "tram",
    )


def test_subway_is_more_specific_than_generic_rail_station() -> None:
    tags = {
        "public_transport": "station",
        "railway": "station",
        "station": "subway",
    }
    assert _transit_mode(tags) == "subway"


def test_ambiguous_public_transport_remains_unclassified() -> None:
    tags = {"public_transport": "platform"}
    assert _transit_mode(tags) is None
    assert _classification(tags) == (
        "transit",
        "public_transport",
        "platform",
        None,
    )
