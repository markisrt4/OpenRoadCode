#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

VALHALLA_SRC="${VALHALLA_SRC:-/src/valhalla}"
PRIME_SERVER_SRC="${PRIME_SERVER_SRC:-/src/prime_server}"

BUILD_JOBS="${BUILD_JOBS:-4}"
CLEAN_BUILD="${CLEAN_BUILD:-0}"

PRIME_BUILD_DIR="${PRIME_BUILD_DIR:-build}"
VALHALLA_BUILD_DIR="${VALHALLA_BUILD_DIR:-build}"

INSTALL_PREFIX="${INSTALL_PREFIX:-/opt/valhalla-build}"

if [[ ! -d "$PRIME_SERVER_SRC/.git" ]]; then
    echo "prime_server source not found: $PRIME_SERVER_SRC" >&2
    exit 1
fi

if [[ ! -d "$VALHALLA_SRC/.git" ]]; then
    echo "Valhalla source not found: $VALHALLA_SRC" >&2
    exit 1
fi

# These repositories are bind-mounted from the host and therefore commonly
# have host UID/GID ownership that differs from the container user. Git 2.35+
# rejects such repositories unless explicitly marked safe.
git config --global --add safe.directory "$PRIME_SERVER_SRC"
git config --global --add safe.directory "$VALHALLA_SRC"

mkdir -p "$INSTALL_PREFIX"

if [[ "$CLEAN_BUILD" == "1" ]]; then
    echo "Removing previous build directories..."
    rm -rf \
        "$PRIME_SERVER_SRC/$PRIME_BUILD_DIR" \
        "$VALHALLA_SRC/$VALHALLA_BUILD_DIR"
fi

echo
echo "Building prime_server"
echo "====================="

cd "$PRIME_SERVER_SRC"

cmake -S . -B "$PRIME_BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"

cmake --build "$PRIME_BUILD_DIR" \
    -j"$BUILD_JOBS"

cmake --install "$PRIME_BUILD_DIR"

export PKG_CONFIG_PATH="$INSTALL_PREFIX/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$INSTALL_PREFIX/lib:${LD_LIBRARY_PATH:-}"

echo
echo "Building Valhalla"
echo "================="

cd "$VALHALLA_SRC"

git submodule sync --recursive
git submodule update --init --recursive

cmake -S . -B "$VALHALLA_BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
    -DENABLE_TESTS=OFF \
    -DENABLE_BENCHMARKS=OFF \
    -DENABLE_PYTHON_BINDINGS=OFF \
    -DENABLE_TOOLS=ON \
    -DENABLE_DATA_TOOLS=ON \
    -DENABLE_HTTP=ON \
    -DENABLE_SERVICES=ON \
    -DENABLE_SINGLE_FILES_WERROR=OFF

cmake --build "$VALHALLA_BUILD_DIR" \
    -j"$BUILD_JOBS"

cmake --install "$VALHALLA_BUILD_DIR"

echo
echo "Valhalla build complete."
echo "Install prefix: $INSTALL_PREFIX"

echo
echo "Installed binaries:"
find "$INSTALL_PREFIX/bin" \
    -maxdepth 1 \
    -type f \
    -printf '  %f\n' \
    2>/dev/null || true

echo
echo "Runtime library check:"
LD_LIBRARY_PATH="$INSTALL_PREFIX/lib" \
    ldd "$INSTALL_PREFIX/bin/valhalla_service" \
    | grep -E 'not found|prime_server' \
    || true
