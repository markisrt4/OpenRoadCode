# MapLibre Build Container

This directory provides an isolated build environment for MapLibre Native and
the OpenRoadCode native map renderer. It keeps the large C++ dependency stack
off the host while writing source and build outputs into a host-mounted source
directory.

## Current reproducibility status

The workflow pins MapLibre Native to commit
`b0388d186d582a8535aa3c03e3cc2ef98cb70dc0` and initializes the submodules
recorded by that commit. The build scripts also select the compiler, CMake
preset, target, and OpenRoadCode CMake paths explicitly.

It is reproducible at the source and build-command level, but it is not yet a
bit-for-bit hermetic build. `debian:trixie` and its APT packages are not pinned
to an image digest or snapshot date, so rebuilding the container later can
select newer compilers and libraries. The host container engine and kernel
also remain outside the definition.

To reach a stricter reproducibility guarantee:

1. Pin the Debian base image by digest.
2. Install packages from a dated Debian snapshot, with versions recorded.
3. Build in CI from a clean source volume and retain the image digest.
4. Record compiler, linker, MapLibre commit, and artifact checksums.
5. Decide whether the goal is a repeatable functional build or identical
   binaries; identical binaries also require normalizing timestamps and paths.

## Host prerequisites

- Docker or a compatible container engine
- An existing host source directory, `$HOME/src` by default
- This repository at `$HOME/src/OpenRoadCode`

Set `CONTAINER_ENGINE` and `HOST_SRC` to use different values. The scripts
mount `HOST_SRC` at `/src`, so both OpenRoadCode and MapLibre Native are visible
inside the container.

## Build the environment

From the repository root:

```bash
development/containers/maplibre/build.sh
```

This builds the `openroadcode-maplibre-builder` image. Override `IMAGE_NAME`
if desired.

## Prepare MapLibre and enter the container

```bash
development/containers/maplibre/run_debug_shell.sh
```

On first use, the script clones MapLibre Native into
`$HOST_SRC/maplibre-native`. On later runs it verifies that the checkout is at
the pinned commit and refuses to silently replace a different checkout. Set
`MAPLIBRE_REF` deliberately to test another commit.

Inside the container, build MapLibre Native and then the renderer:

```bash
/src/OpenRoadCode/development/containers/maplibre/scripts/build_maplibre.sh
/src/OpenRoadCode/development/containers/maplibre/scripts/build_map_renderer.sh
```

The outputs persist on the host at:

```text
$HOST_SRC/maplibre-native/build-linux-opengl
$HOST_SRC/OpenRoadCode/apps/map_renderer/build-container/openroadcode-map-renderer
```

`BUILD_JOBS` controls parallel compilation. The renderer script also accepts
`OPENROADCODE_SRC`, `MAPLIBRE_SRC`, `MAPLIBRE_BUILD`, and
`RENDERER_BUILD_DIR` overrides.

## Runtime dependencies

The container is intended for compilation. Running the graphical renderer on
the host still requires its GL/GLFW runtime libraries, offline map data, and
the style described in `apps/map_renderer/README.md`. `host_setup.sh` installs
the currently known Debian/Ubuntu host packages, but should be reviewed before
use because it invokes `sudo apt` and is not part of the reproducible build.

The tile-generation workflow is separate; see `scripts/README.md`.

