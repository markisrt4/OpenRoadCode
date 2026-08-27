# Map Renderer Protocol

This package is the Python client contract for the native C++ map renderer.
`MapRendererClient` serializes one JSON command per Unix-domain socket
connection and raises `MapRendererUnavailableError` when the renderer cannot
be reached.

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

The default socket is `/tmp/openroadcode-map-renderer.sock`; pass a different
path to `MapRendererClient` when the renderer uses a custom socket. Route data
is sent as a GeoJSON object with `set_route()`. `fit_bounds()` frames a route,
and `set_position()` updates the vehicle marker. See
`apps/map_renderer/README.md` for the native process and style requirements.
