# Route Planning

The `controllers.route_planning` package provides provider-neutral routing
types and a Valhalla-backed controller. It can calculate a route, decode the
returned polyline into geographic points, convert that shape to GeoJSON, and
present it through the native map renderer.

Applications should depend on `RoutePlanningControllerIf` and use
`RouteRequest`, `RouteResult`, and `TravelMode` as the public contract.
`ValhallaRoutePlanningController` is the current implementation and delegates
HTTP calls to `protocols.valhalla.ValhallaHttpClient`.

## Example

```python
from controllers.route_planning.route_planning_types import (
    GeoPoint, RouteRequest,
)
from controllers.route_planning.valhalla_route_planning_controller import (
    ValhallaRoutePlanningController,
)
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient

planner = ValhallaRoutePlanningController(ValhallaHttpClient())
route = planner.calculate_route(
    RouteRequest(
        origin=GeoPoint(latitude=42.3314, longitude=-83.0458),
        destination=GeoPoint(latitude=42.2808, longitude=-83.7430),
    )
)
```

To draw the result and fit the camera to its bounds:

```python
from controllers.route_planning.route_map_presenter import present_route
from protocols.map_renderer.map_renderer_client import MapRendererClient

present_route(route, MapRendererClient())
```

This requires both Valhalla and the native map renderer to be running.

## Component test

The component test queries a real Valhalla service, prints directions, and
offers the route to the native renderer:

```bash
python3 -m controllers.route_planning.component_test.valhalla_route_planning_cli \
  --origin-lat 42.3314 --origin-lon -83.0458 \
  --destination-lat 42.2808 --destination-lon -83.7430
```

Pass `--url` for a non-default Valhalla endpoint or `--geojson-output PATH` to
save the route independently of the renderer.

## Route simulation demos

The component-test package also contains three interactive demos. Their
default route uses public Detroit-area coordinates; every origin and
destination can be overridden on the command line.

```bash
# Move a vehicle marker through the decoded route shape.
python3 -m controllers.route_planning.component_test.valhalla_route_drive_demo_cli

# Follow sampled route points with a pitched, bearing-aware camera.
python3 -m controllers.route_planning.component_test.valhalla_route_follow_demo_cli

# Interpolate movement at a fixed speed and smooth position and bearing.
python3 -m controllers.route_planning.component_test.valhalla_route_smooth_follow_demo_cli
```

All three require a running Valhalla service, the native renderer, and a map
style containing both `route` and `vehicle` GeoJSON sources. Use `--help` to
see timing, camera, endpoint, and smoothing controls. The defaults are
deliberately accelerated demonstrations rather than realistic driving input.
