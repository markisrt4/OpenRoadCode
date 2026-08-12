from controllers.route_planning.route_geojson_mapper import (
    route_to_geojson,
)
from controllers.route_planning.route_planning_types import (
    GeoPoint,
    RouteManeuver,
    RouteResult,
)


def test_route_to_geojson() -> None:
    route = RouteResult(
        distance_miles=12.5,
        duration_seconds=900.0,
        shape=(
            GeoPoint(
                latitude=42.3500,
                longitude=-83.1000,
            ),
            GeoPoint(
                latitude=42.3314,
                longitude=-83.0458,
            ),
        ),
        maneuvers=(),
    )

    result = route_to_geojson(route)

    assert result == {
        "type": "Feature",
        "properties": {
            "distance_miles": 12.5,
            "duration_seconds": 900.0,
        },
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [-83.1000, 42.3500],
                [-83.0458, 42.3314],
            ],
        },
    }
