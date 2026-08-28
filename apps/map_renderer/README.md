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

Map and Valhalla data are intentionally built and deployed separately; see [Navigation deployment](../../docs/navigation_deployment.md).

The container workflow is source-repeatable but not yet bit-for-bit hermetic. Its Debian base image and APT packages still float. The guide records this limitation and the remaining work needed for a stricter reproducibility guarantee.
