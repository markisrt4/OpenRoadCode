## Map/style data

The canonical deployed style is:

```text
/srv/openroadcode/maps/styles/openroadcode.json
```

It is produced by `tools/map_builder` and travels with the map dataset. It references the deployed MBTiles archive and glyphs and defines the `route` and `vehicle` GeoJSON sources.

Do not hard-code a region-specific style filename such as `michigan-test.json` in runtime code. Region selection belongs to the map-builder dataset; renderer configuration points at the stable `openroadcode.json` deployment path.

## Build

MapLibre Native must first be built with its Linux OpenGL preset. The [MapLibre build-container guide](https://github.com/markisrt4/OpenRoadCode/blob/master/development/containers/maplibre/README.md) provides the recommended isolated workflow. It pins the tested MapLibre commit, mounts the host source directory into the container, and includes scripts for building both MapLibre and this executable.

For a complete vehicle software build/install, prefer:

```bash
./scripts/installers/install_navigation_stack.sh --target rpi5
```

The navigation-stack installer builds MapLibre Native and the OpenRoadCode renderer in the container and installs the executable beneath:

```text
/opt/openroadcode/navigation/bin/
```

Map and Valhalla data are intentionally built and deployed separately; see [Navigation deployment](https://github.com/markisrt4/OpenRoadCode/blob/master/docs/navigation_deployment.md).

The container workflow is source-repeatable but not yet bit-for-bit hermetic. Its Debian base image and APT packages still float. The guide records this limitation and the remaining work needed for a stricter reproducibility guarantee.

## Logging

The renderer emits structured JSON Lines to stderr through `libspdlog`. The UI
launcher collects its output into the shared rotating ORC store. Use
`./runOrcUi --follow-logs` for readable live output, or attach separately with
`python -m common.logging.viewer --component map_renderer`.
See [ORC logging](../../common/logging/README.md) for settings, storage, and CI gates.

## Mouse and toolbar camera controls

The renderer reports camera changes back to Navigation so mouse zoom and pan
are reflected in toolbar values. The last observed camera is retained across
screen changes within the current ORC session.

The navigation dimension button switches between 3D (tilted) and 2D (overhead);
its label shows the view it will select. Switching to 2D preserves the current
center and zoom and replaces extruded buildings with flat footprints. Tilt
buttons update the dimension label as well. House-number labels are hidden in
3D and appear in 2D from zoom 17 to reduce building clutter.

Toolbar camera commands end active mouse gestures and cancel pending camera
animations before applying the requested view. Losing native-window focus also
clears drag state, including when a mouse release is missed during a transition
back to Tk controls. Position-marker and POI updates do not cancel gestures.

Shared Python publishers serialize complete multipart messages so UI camera
commands cannot interleave with navigation updates. The native command receiver
drains and rejects malformed multipart messages without blocking the render loop.

For a manual regression check, pan by dragging, zoom with the mouse wheel, and
then try the pan arrows, zoom buttons, 3D, north-up, and recenter controls. Also
start dragging and move/release outside the map before pressing a toolbar button.
Recenter should restore position following; manual pan should suspend it.

This behavior is implemented in the native renderer. A repository update alone
does not update an already installed executable. In Termux, an existing renderer
build can be updated without rebuilding MapLibre or Valhalla:

```bash
cd ~/src/OpenRoadCode
git switch android-linux-food-apps
./development/termux/build_navigation_stack.sh --renderer-only
```

The renderer-only option installs renderer dependencies, including `libspdlog`, and stops before
installation if compilation fails. It reuses the configured MapLibre build and
does not rebuild Valhalla or download map data.

Close ORC before updating the executable, then restart it. The build directory
must have been configured by `development/termux/build_navigation_stack.sh`.
