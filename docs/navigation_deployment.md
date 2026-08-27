# Navigation Build and Deployment

OpenRoadCode deliberately separates navigation software, vehicle-local configuration, and large generated map/routing data. This allows the vehicle computer to remain a lean runtime target while a separate build machine performs expensive map generation.

## Filesystem contract

```text
/opt/openroadcode/navigation/
    installed software
    ├── bin/openroadcode-map-renderer
    └── valhalla/

/etc/openroadcode/
    navigation.toml

/srv/openroadcode/
    build-manifest.json
    maps/
    └── valhalla/
```

Ownership by purpose:

| Path | Owner/purpose |
| --- | --- |
| `/opt/openroadcode/navigation` | Installed navigation executables and libraries |
| `/etc/openroadcode/navigation.toml` | Vehicle-local runtime configuration |
| `/srv/openroadcode` | Versioned/deployable map and routing dataset |
| `/srv/openroadcode-update` | Temporary incoming dataset on the vehicle |
| `/srv/openroadcode-previous` | Previous dataset retained for rollback |

Map updates must not overwrite `/etc/openroadcode`.

## Architecture

```text
MAP BUILD MACHINE                         VEHICLE / RASPBERRY PI
-----------------                         ----------------------
Geofabrik OSM extracts
        |
        v
tools/map_builder
  - build MBTiles
  - build glyph/style package
  - build Valhalla tiles
  - validate artifacts
  - write build-manifest.json
        |
        | SSH + rsync, initiated by vehicle
        v
                                    /srv/openroadcode-update
                                             |
                                          validate
                                             |
                                      atomic-ish promotion
                                             |
                                    /srv/openroadcode
                                             |
                                      restart Valhalla
                                             |
                                      rollback on failure
```

The map-build machine is the authoritative producer of navigation data. The vehicle controls when it consumes a new dataset.

## 1. Install navigation software on the vehicle

From the OpenRoadCode repository on the Raspberry Pi:

```bash
./scripts/installers/install_navigation_stack.sh --target rpi5
```

Preview without modifying the system:

```bash
./scripts/installers/install_navigation_stack.sh --target rpi5 --show-plan
```

The installer builds/installs MapLibre Native integration, the OpenRoadCode native renderer, and Valhalla software beneath `/opt/openroadcode/navigation`.

It does **not** build map data. Map generation belongs on the map-build machine.

The installer seeds `/etc/openroadcode/navigation.toml` from `config/navigation.toml` only when the deployed file does not already exist. Existing local configuration is preserved.

If Valhalla map data are not present yet, service installation is deferred until data have been deployed.

## 2. Build map/routing data on the build machine

From `tools/map_builder`:

```bash
./scripts/build-image.sh
./scripts/run-builder.sh build --regions north-america/us/michigan
```

Or select regions interactively:

```bash
./scripts/run-builder.sh tui
```

Successful output is written under `tools/map_builder/build-output/` using the same `/srv/openroadcode` paths expected by the vehicle.

The builder validates its output and writes `build-manifest.json`. A dataset without that manifest is not considered deployable.

See `tools/map_builder/README.md` for builder details and toolchain pinning.

## 3. Publish the dataset on the build machine

The vehicle pull script expects an SSH/rsync-readable directory containing the **contents** of the generated `/srv/openroadcode` tree.

A simple deployment on the build machine is:

```bash
cd tools/map_builder
./scripts/deploy-to-srv.sh
```

This makes `/srv/openroadcode` on the build machine the published dataset root.

SSH key authentication is recommended for unattended vehicle pulls. The vehicle only needs read access to the published tree.

## 4. Pull map data from the vehicle

First preview the transfer:

```bash
./scripts/runtime/pull_navigation_data.sh \
  --source mapbuilder@MAP_HOST:/srv/openroadcode \
  --dry-run
```

Then deploy:

```bash
./scripts/runtime/pull_navigation_data.sh \
  --source mapbuilder@MAP_HOST:/srv/openroadcode
```

The updater:

1. reads the remote `build-manifest.json` before transfer;
2. skips the update when the local and remote manifests already match;
3. downloads into `/srv/openroadcode-update`;
4. preserves vehicle-owned `maps/routes/` data;
5. validates the staged deployment contract;
6. verifies that the staged manifest is the same manifest checked before transfer;
7. moves the previous dataset to `/srv/openroadcode-previous`;
8. promotes the staged dataset to `/srv/openroadcode`;
9. restarts Valhalla when its service is installed;
10. restores the previous dataset if Valhalla fails after promotion.

Useful options:

```text
--dry-run       preview rsync changes
--force         pull even when manifests match
--no-restart    do not restart Valhalla after promotion
```

The source can also be provided through `NAVIGATION_DATA_SOURCE`.

## Runtime renderer configuration

`/etc/openroadcode/navigation.toml` selects runtime behavior without changing the deployed dataset:

```toml
[map_renderer]
style = "/srv/openroadcode/maps/styles/openroadcode.json"
cache = "/var/cache/openroadcode/maplibre.db"

[vehicle_marker]
mode = "vehicle"
scale = 1.0
```

Supported marker modes are `blue_dot`, `heading`, and `vehicle`. Marker selection is local configuration; the style definitions themselves travel with the map package.

The intended `vehicle` presentation is a top-down red Hyundai Veloster. Until that artwork is added to the map/style asset package, the style uses a red placeholder marker.

## Updating marker choice

Edit the vehicle-local config:

```bash
sudo editor /etc/openroadcode/navigation.toml
```

For example:

```toml
[vehicle_marker]
mode = "blue_dot"
scale = 1.0
```

Restart the renderer after changing startup configuration.

## Validation and troubleshooting

Before first use after pulling repository changes:

```bash
bash -n scripts/installers/install_navigation_stack.sh
bash -n scripts/runtime/pull_navigation_data.sh
python3 -m pytest tools/map_builder/tests -v
```

Useful runtime checks on the vehicle include:

```bash
test -x /opt/openroadcode/navigation/bin/openroadcode-map-renderer
test -s /etc/openroadcode/navigation.toml
test -s /srv/openroadcode/build-manifest.json
test -s /srv/openroadcode/maps/styles/openroadcode.json
test -s /srv/openroadcode/valhalla/valhalla.json
systemctl status valhalla.service
```

If a data promotion causes Valhalla to fail, `pull_navigation_data.sh` attempts automatic rollback. `/srv/openroadcode-previous` also provides an administrator-visible copy of the previous successful dataset until the next promotion.

## Design rules

- Build expensive map/routing data off-vehicle.
- Install executable software under `/opt`.
- Keep machine/vehicle configuration under `/etc`.
- Keep generated navigation data under `/srv`.
- Do not bake region names such as `michigan-test` into renderer code.
- Do not let map-data synchronization overwrite vehicle-local configuration.
- Treat `build-manifest.json` as the deployment identity and validation boundary.
- Preserve runtime-generated route/debug data across map updates.
