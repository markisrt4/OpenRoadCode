#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
HOST_SRC="${HOST_SRC:-$HOME/src}"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/openroadcode/navigation}"
DATA_ROOT="${DATA_ROOT:-/srv/openroadcode}"
BUILD_ROOT="${BUILD_ROOT:-$PROJECT_ROOT/build/navigation-stack}"
MAPLIBRE_SRC="${MAPLIBRE_SRC:-$HOST_SRC/maplibre-native}"
VALHALLA_SRC="${VALHALLA_SRC:-$HOST_SRC/valhalla}"
PRIME_SERVER_SRC="${PRIME_SERVER_SRC:-$HOST_SRC/prime_server}"
MAPLIBRE_REF="${MAPLIBRE_REF:-b0388d186d582a8535aa3c03e3cc2ef98cb70dc0}"

TOOLCHAIN_LOCK="$PROJECT_ROOT/tools/map_builder/toolchain.lock"
if [[ -f "$TOOLCHAIN_LOCK" ]]; then
  # shellcheck disable=SC1090
  source "$TOOLCHAIN_LOCK"
fi
VALHALLA_REF="${VALHALLA_REF:-${VALHALLA_COMMIT:-}}"
PRIME_SERVER_REF="${PRIME_SERVER_REF:-}"

SHOW_PLAN=0
SKIP_HOST_PACKAGES=0
SKIP_MAPLIBRE=0
SKIP_VALHALLA=0
SKIP_SERVICES=0
SKIP_SMOKE=0
TARGET="rpi5"

usage() {
  cat <<EOF
Usage: $0 [options]

Build and install the OpenRoadCode navigation software stack.

Software is installed beneath:
  $INSTALL_ROOT

Map and routing data are managed separately beneath:
  $DATA_ROOT

Options:
  --target TARGET         host_setup target (rpi4, rpi5, linux-dev; default: rpi5)
  --show-plan             print the resolved plan without changing the system
  --skip-host-packages    do not invoke host package setup
  --skip-maplibre         skip MapLibre Native and renderer build/install
  --skip-valhalla         skip Valhalla build/install
  --skip-services         skip systemd service installation
  --skip-smoke            skip final software smoke checks
  -h, --help              show this help

Map/routing data are intentionally NOT built here. Use tools/map_builder on the
map-build machine, then pull validated data onto the vehicle with:
  scripts/runtime/pull_navigation_data.sh

Environment overrides include CONTAINER_ENGINE, HOST_SRC, INSTALL_ROOT,
DATA_ROOT, BUILD_ROOT, MAPLIBRE_REF, VALHALLA_REF, PRIME_SERVER_REF, and
BUILD_JOBS.
EOF
}

while (( $# > 0 )); do
  case "$1" in
    --target)
      shift; TARGET="${1:?--target requires a value}" ;;
    --show-plan) SHOW_PLAN=1 ;;
    --skip-host-packages) SKIP_HOST_PACKAGES=1 ;;
    --skip-maplibre) SKIP_MAPLIBRE=1 ;;
    --skip-valhalla) SKIP_VALHALLA=1 ;;
    --skip-services) SKIP_SERVICES=1 ;;
    --skip-smoke) SKIP_SMOKE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

case "$TARGET" in
  rpi4|rpi5|linux-dev) ;;
  *) echo "Unsupported target: $TARGET" >&2; exit 2 ;;
esac

cat <<EOF
OpenRoadCode navigation software plan
  target:             $TARGET
  container engine:   $CONTAINER_ENGINE
  host source root:   $HOST_SRC
  software install:   $INSTALL_ROOT
  runtime data root:  $DATA_ROOT
  staging/build root: $BUILD_ROOT
  MapLibre ref:       $MAPLIBRE_REF
  Valhalla ref:       ${VALHALLA_REF:-UNPINNED}
  prime_server ref:   ${PRIME_SERVER_REF:-UNPINNED}
  map-data build:     external / not performed here
EOF

if [[ -z "$PRIME_SERVER_REF" ]] && (( ! SKIP_VALHALLA )); then
  echo "[!] prime_server is not pinned yet; this build is functionally repeatable, not fully reproducible." >&2
fi

if (( SHOW_PLAN )); then
  echo "Plan only; no changes made."
  exit 0
fi

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
command -v "$CONTAINER_ENGINE" >/dev/null 2>&1 || {
  echo "Container engine not found: $CONTAINER_ENGINE" >&2
  exit 1
}

mkdir -p "$BUILD_ROOT" "$HOST_SRC"

checkout_repo() {
  local url="$1" dir="$2" ref="$3" label="$4"
  if [[ ! -d "$dir/.git" ]]; then
    echo "[*] Cloning $label..."
    git clone "$url" "$dir"
  fi
  if [[ -n "$ref" ]]; then
    echo "[*] Checking out $label at $ref"
    git -C "$dir" fetch --tags --prune origin
    git -C "$dir" checkout --detach "$ref"
  fi
  git -C "$dir" submodule sync --recursive
  git -C "$dir" submodule update --init --recursive
}

if (( ! SKIP_HOST_PACKAGES )); then
  echo "[*] Installing host prerequisites"
  bash "$PROJECT_ROOT/scripts/installers/host_setup.sh" \
    --target "$TARGET" \
    --feature desktop-ui \
    --feature gps \
    --no-vnc \
    --no-gpsd-service
  sudo apt-get update
  sudo apt-get install -y rsync libglfw3 libshp4 libgles2 libuv1
fi

if (( ! SKIP_MAPLIBRE )); then
  checkout_repo \
    "https://github.com/maplibre/maplibre-native.git" \
    "$MAPLIBRE_SRC" "$MAPLIBRE_REF" "MapLibre Native"

  echo "[*] Building MapLibre builder image"
  bash "$PROJECT_ROOT/development/containers/maplibre/build.sh"

  echo "[*] Building MapLibre Native and OpenRoadCode renderer"
  "$CONTAINER_ENGINE" run --rm \
    --volume "$HOST_SRC:/src" \
    --workdir /src \
    -e BUILD_JOBS="${BUILD_JOBS:-4}" \
    openroadcode-maplibre-builder \
    /bin/bash -lc "
      set -euo pipefail
      /src/OpenRoadCode/development/containers/maplibre/scripts/build_maplibre.sh
      /src/OpenRoadCode/development/containers/maplibre/scripts/build_map_renderer.sh
    "

  renderer="$PROJECT_ROOT/apps/map_renderer/build-container/openroadcode-map-renderer"
  [[ -x "$renderer" ]] || { echo "Renderer build missing: $renderer" >&2; exit 1; }
  sudo install -d "$INSTALL_ROOT/bin"
  sudo install -m 0755 "$renderer" "$INSTALL_ROOT/bin/openroadcode-map-renderer"
fi

if (( ! SKIP_VALHALLA )); then
  checkout_repo \
    "https://github.com/kevinkreiser/prime_server.git" \
    "$PRIME_SERVER_SRC" "$PRIME_SERVER_REF" "prime_server"
  checkout_repo \
    "https://github.com/valhalla/valhalla.git" \
    "$VALHALLA_SRC" "$VALHALLA_REF" "Valhalla"

  echo "[*] Building Valhalla builder image"
  bash "$PROJECT_ROOT/development/containers/valhalla/build.sh"

  valhalla_stage="$BUILD_ROOT/valhalla"
  rm -rf "$valhalla_stage"
  mkdir -p "$valhalla_stage"

  echo "[*] Building Valhalla and prime_server"
  "$CONTAINER_ENGINE" run --rm \
    --volume "$HOST_SRC:/src" \
    --workdir /src \
    -e BUILD_JOBS="${BUILD_JOBS:-4}" \
    -e INSTALL_PREFIX="/src/OpenRoadCode/build/navigation-stack/valhalla" \
    openroadcode-valhalla-builder \
    /bin/bash -lc "/src/OpenRoadCode/development/containers/valhalla/scripts/build_valhalla.sh"

  [[ -x "$valhalla_stage/bin/valhalla_service" ]] || {
    echo "Valhalla build missing: $valhalla_stage/bin/valhalla_service" >&2
    exit 1
  }

  sudo install -d "$INSTALL_ROOT"
  sudo rsync -a --delete "$valhalla_stage/" "$INSTALL_ROOT/valhalla/"

  sudo install -d /etc/ld.so.conf.d
  printf '%s\n' "$INSTALL_ROOT/valhalla/lib" \
    | sudo tee /etc/ld.so.conf.d/openroadcode-navigation.conf >/dev/null
  sudo ldconfig
fi

if (( ! SKIP_SERVICES )) && (( ! SKIP_VALHALLA )); then
  valhalla_config="$DATA_ROOT/valhalla/valhalla.json"
  echo "[*] Installing Valhalla systemd service"
  if [[ ! -f "$valhalla_config" ]]; then
    echo "[!] Map/routing data are not installed yet: $valhalla_config" >&2
    echo "[!] Installing the service is deferred until pull_navigation_data.sh provides data." >&2
  else
    sudo env \
      PATH="$INSTALL_ROOT/valhalla/bin:$PATH" \
      bash "$PROJECT_ROOT/scripts/systemd/install_valhalla_systemd.sh" \
        "$valhalla_config" 1
  fi
fi

if (( ! SKIP_SMOKE )); then
  echo "[*] Running software smoke checks"
  if (( ! SKIP_MAPLIBRE )); then
    test -x "$INSTALL_ROOT/bin/openroadcode-map-renderer"
  fi
  if (( ! SKIP_VALHALLA )); then
    test -x "$INSTALL_ROOT/valhalla/bin/valhalla_service"
  fi
fi

echo
echo "[+] Navigation software installation complete"
echo "    software: $INSTALL_ROOT"
echo "    data:     $DATA_ROOT (managed separately)"
echo "    updater:  $PROJECT_ROOT/scripts/runtime/pull_navigation_data.sh"
