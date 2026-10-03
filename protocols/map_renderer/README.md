# Map Renderer Protocol

This package is the Python client contract for the native C++ map renderer.
`MapRendererClient` publishes asynchronous JSON commands on the ORC ZeroMQ
message bus over TCP. A successful publication does not acknowledge renderer
receipt or application. `MapRendererUnavailableError` reports local publication
failures.

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
