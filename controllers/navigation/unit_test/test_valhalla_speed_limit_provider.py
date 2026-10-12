# SPDX-License-Identifier: MIT
"""Mapped speed-limit selection and uncertainty handling."""

from copy import deepcopy
from unittest.mock import Mock
import pytest

from controllers.navigation.valhalla_speed_limit_provider import ValhallaSpeedLimitProvider
from ui.navigation.map_ui_if import GeoPoint


def response():
    return {"units": "kilometers", "confidence_score": 1,
            "edges": [{"id": 1, "speed_limit": 30}, {"id": 2, "speed_limit": 72, "names": ["Example Road"]}],
            "matched_points": [{"type": "matched", "edge_index": 1, "distance_from_trace_point": 2}]}


def test_uses_current_matched_edge_and_converts_kph_to_si():
    client = Mock()
    client.trace_attributes.return_value = response()
    result = ValhallaSpeedLimitProvider(client).lookup((GeoPoint(0.7, -1.4), GeoPoint(0.71, -1.4)))
    assert result.limit_mps == 20
    assert result.road_name == "Example Road"
    request = client.trace_attributes.call_args.args[0]
    assert request["directions_options"]["units"] == "kilometers"
    assert request["shape_match"] == "map_snap"
    assert "edge.speed_limit" in request["filters"]["attributes"]


@pytest.mark.parametrize("speed", [None, 0, -1, 255, "unlimited", float("nan"), True])
def test_missing_or_invalid_limit_never_uses_inferred_routing_speed(speed):
    result = response()
    result["edges"][1].update(speed_limit=speed, speed=100)
    client = Mock()
    client.trace_attributes.return_value = result
    assert ValhallaSpeedLimitProvider(client).lookup(()).limit_mps is None


@pytest.mark.parametrize("change", ["unmatched", "far", "ambiguous", "weak", "bad_units", "bad_index"])
def test_unusable_match_is_unknown(change):
    result = response()
    if change == "unmatched":
        result["matched_points"][0]["type"] = "unmatched"
    elif change == "far":
        result["matched_points"][0]["distance_from_trace_point"] = 50
    elif change == "weak":
        result["confidence_score"] = 0.2
    elif change == "bad_units":
        result["units"] = "miles"
    elif change == "bad_index":
        result["matched_points"][0]["edge_index"] = 99
    else:
        alternative = deepcopy(result)
        alternative["edges"][1]["id"] = 99
        alternative["confidence_score"] = 0.95
        result["alternate_paths"] = [alternative]
    client = Mock()
    client.trace_attributes.return_value = result
    assert ValhallaSpeedLimitProvider(client).lookup(()).limit_mps is None
