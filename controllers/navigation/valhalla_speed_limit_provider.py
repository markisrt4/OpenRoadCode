# SPDX-License-Identifier: MIT
"""Read mapped limits, never inferred routing speeds, from Valhalla traces."""

import math
from typing import Any

from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from ui.navigation.map_ui_if import GeoPoint
from ui.navigation.road_speed_limit_ui_if import RoadSpeedLimitState


def matched_edge(result: dict[str, Any]) -> dict[str, Any] | None:
    points, edges = result.get("matched_points"), result.get("edges")
    if not isinstance(points, list) or not points or not isinstance(edges, list):
        return None
    point = points[-1]
    if not isinstance(point, dict) or point.get("type") != "matched":
        return None
    index, distance = point.get("edge_index"), point.get("distance_from_trace_point")
    if type(index) is not int or not 0 <= index < len(edges):
        return None
    if not isinstance(distance, (int, float)) or isinstance(distance, bool) or not math.isfinite(distance) or not 0 <= distance <= 20:
        return None
    if point.get("begin_route_discontinuity") or point.get("end_route_discontinuity"):
        return None
    return edges[index] if isinstance(edges[index], dict) else None


class ValhallaSpeedLimitProvider:
    def __init__(self, client: ValhallaHttpClient) -> None:
        self._client = client

    def lookup(self, trace: tuple[GeoPoint, ...]) -> RoadSpeedLimitState:
        result = self._client.trace_attributes({
            "shape": [{"lat": math.degrees(p.latitude_rad), "lon": math.degrees(p.longitude_rad)} for p in trace],
            "shape_match": "map_snap", "costing": "auto", "best_paths": 2,
            "directions_options": {"units": "kilometers"},
            "filters": {"action": "include", "attributes": ["edge.id", "edge.names", "edge.speed_limit",
                "matched.type", "matched.edge_index", "matched.distance_from_trace_point",
                "matched.begin_route_discontinuity", "matched.end_route_discontinuity"]},
        })
        confidence = result.get("confidence_score")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence) or not 0.8 <= confidence <= 1:
            return RoadSpeedLimitState()
        edge = matched_edge(result)
        if edge is None or result.get("units") != "kilometers":
            return RoadSpeedLimitState()
        alternatives = result.get("alternate_paths", [])
        if not isinstance(alternatives, list):
            return RoadSpeedLimitState()
        for alternative in alternatives:
            if not isinstance(alternative, dict):
                return RoadSpeedLimitState()
            other = matched_edge(alternative)
            confidence = alternative.get("confidence_score", 0)
            if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not math.isfinite(confidence):
                return RoadSpeedLimitState()
            if other and confidence >= 0.9 and other.get("id") != edge.get("id"):
                return RoadSpeedLimitState()
        speed = edge.get("speed_limit")
        if not isinstance(speed, (int, float)) or isinstance(speed, bool) or not math.isfinite(speed) or not 0 < speed < 255:
            return RoadSpeedLimitState()
        names = edge.get("names", [])
        name = names[0] if isinstance(names, list) and names and isinstance(names[0], str) else ""
        return RoadSpeedLimitState(speed / 3.6, name)
