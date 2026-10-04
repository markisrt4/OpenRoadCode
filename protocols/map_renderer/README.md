# Map Renderer Protocol

This package is the Python client contract for the native C++ map renderer.
`MapRendererClient` publishes asynchronous JSON commands on the ORC ZeroMQ
message bus over TCP. A successful publication does not acknowledge renderer
receipt or application. `MapRendererUnavailableError` reports local publication
failures.
Replay state after launching or replacing the renderer.

```python
from protocols.map_renderer.map_renderer_client import MapRendererClient

renderer = MapRendererClient()
renderer.set_camera(
    latitude=42.3314,
    longitude=-83.0458,
    zoom=14.0,
    bearing=0.0,
    pitch=30.0,
)
```

The default publisher endpoint is `tcp://127.0.0.1:5556`; pass `endpoint=` to
`MapRendererClient` to select another broker. The native renderer subscribes
through `tcp://127.0.0.1:5557`. Route data is sent as a GeoJSON object with
`set_route()`. `fit_bounds()` frames a route, and `set_position()` updates the
vehicle marker. See [the renderer documentation](../../apps/map_renderer/README.md)
for the native process and style requirements, and [ORC logging](../../common/logging/README.md)
for structured logs and live viewing.

`set_route_weather(geojson)` updates a separate `route-weather` GeoJSON source
without changing route geometry, POI results, radar visibility, or the camera.
Point features use a `label` string for forecast text; an empty FeatureCollection
clears them. The native renderer adds purple circles and haloed text above the
base style at startup. Rebuild the native renderer to use this command.

`set_weather_field(tile_url, enabled=True, frame_time=..., opacity=0.45,
max_zoom=9)` controls one independent temperature/wind raster source. It uses the
same validated tile URL/opacity/zoom contract as radar but leaves radar, locator
rings, route geometry and camera state unchanged. Model heatmaps render below
radar and navigation overlays. Disable with `tile_url=None, enabled=False`.

`set_city_weather(geojson)` updates an independent `city-weather` source with
large values and smaller city names. Point properties are `name`, `value` and
`color`. An empty FeatureCollection clears this overlay. It does not change
route weather, POI selection, heatmaps, radar, the camera or position rings.

`search_weather_cities(request_id)` discovers up to twelve spaced city/town
points in the current viewport from the offline vector `openroad` source's
`place` layer. Replies use `map.weather.cities` with the same integer
`request_id` and `cities: [{name, latitude, longitude}, ...]`. The city subscriber
is independent of POI subscriptions, and ignores replies to obsolete requests.
Rebuild the native navigation stack before enabling this overlay.

City-weather GeoJSON features may carry an opaque `weather_city_id` beginning
with `weather-city:`. A rendered-feature hit publishes that identity through the
existing `map.click.marker_id`, with no POI `marker_index`. Weather consumers
resolve it against currently displayed cities; POI consumers ignore these hits.
Ordinary clicks and POI marker behavior remain unchanged. Rebuild the native
renderer to enable this hit testing.

## Camera feedback

The renderer publishes `map.camera.changed` after camera changes, at most once
per 50 milliseconds. Its numeric fields are `latitude`, `longitude`, `zoom`,
`bearing`, and `pitch`; coordinates and angles are in degrees. Navigation drains
the queue to the newest valid snapshot, updates its control values, and retains
the actual camera in the shared request handler without sending a feedback
command. Native gestures therefore update toolbar state, and returning to
Navigation restores the last observed camera during the current ORC session.
Camera feedback starts after an explicit UI camera command so the renderer's
startup dataset view cannot overwrite the intended navigation camera.
