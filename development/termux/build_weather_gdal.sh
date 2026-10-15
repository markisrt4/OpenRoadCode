#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
# Build only the raster tools needed by ORC weather, outside the Termux prefix.
set -euo pipefail

GDAL_VERSION=3.13.3
GDAL_SHA256=a3348c2102dd91962290007d7c293b467bb1b0cd89f086f24bb97b9b653a9804
usage() {
  echo "Usage: bash development/termux/build_weather_gdal.sh [--check]"
  echo "Build and verify isolated GDAL, then activate it for ORC weather."
  echo "ORC_GDAL_BUILD_JOBS defaults to 1 to limit phone memory usage."
  echo "--check verifies the existing isolated installation without building."
}
case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  --check|'') ;;
  *) usage >&2; exit 2 ;;
esac
(( $# <= 1 )) || { usage >&2; exit 2; }
[[ -n "${PREFIX:-}" && ( -n "${TERMUX_VERSION:-}" || "$PREFIX" == *com.termux* ) ]] || {
  echo "Run this builder in native Termux, outside proot." >&2; exit 2;
}
: "${TMPDIR:?Termux TMPDIR must be set}"
ORC_GDAL_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
ORC_GDAL_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
ORC_GDAL_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
for path in "$ORC_GDAL_DATA_HOME" "$ORC_GDAL_CACHE_HOME" "$ORC_GDAL_STATE_HOME"; do
  [[ "$path" == /* ]] || { echo "XDG directories must be absolute." >&2; exit 2; }
done
ORC_GDAL_ROOT="$ORC_GDAL_DATA_HOME/openroadcode/tools/gdal"
probe_dir=''
link_tmp=''
cleanup() {
  [[ -z "$probe_dir" ]] || rm -rf -- "$probe_dir"
  [[ -z "$link_tmp" ]] || rm -f -- "$link_tmp"
}
trap cleanup EXIT

verify() {
  local candidate="$1"
  for tool in gdalinfo gdal_translate gdalwarp; do
    [[ -x "$candidate/bin/$tool" ]] || { echo "Missing isolated $tool" >&2; return 1; }
    "$candidate/bin/$tool" --version || return 1
  done
  "$candidate/bin/gdalinfo" --format GRIB || return 1
  "$candidate/bin/gdalinfo" --format JP2OpenJPEG || return 1
  probe_dir="$(mktemp -d "$TMPDIR/orc-gdal-check.XXXXXX")"
  cat > "$probe_dir/input.asc" <<'GRID'
ncols 2
nrows 2
xllcorner -84
yllcorner 42
cellsize 0.5
NODATA_value -9999
10 20
30 40
GRID
  "$candidate/bin/gdal_translate" -q -a_srs EPSG:4326 -of GRIB \
    -co DATA_ENCODING=SIMPLE_PACKING "$probe_dir/input.asc" "$probe_dir/check.grib2" || return 1
  "$candidate/bin/gdalwarp" -q -t_srs EPSG:3857 -ts 8 8 \
    "$probe_dir/check.grib2" "$probe_dir/check.tif" || return 1
  "$candidate/bin/gdalinfo" -json -stats "$probe_dir/check.tif" > "$probe_dir/check.json" || return 1
  python - "$probe_dir/check.json" <<'PY'
import json, math, sys
with open(sys.argv[1]) as stream:
    data = json.load(stream)
if data.get('size') != [8, 8] or len(data.get('bands', [])) != 1:
    raise SystemExit('GDAL smoke check produced an unexpected raster')
band = data['bands'][0]
if not all(math.isfinite(band.get(key, float('nan'))) for key in ('minimum', 'maximum')):
    raise SystemExit('GDAL smoke check produced no valid numeric pixels')
print('GRIB decode, reprojection and GeoTIFF checks passed.')
PY
}

if [[ "${1:-}" == --check ]]; then
  verify "$ORC_GDAL_ROOT/current"
  exit 0
fi
jobs="${ORC_GDAL_BUILD_JOBS:-1}"
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo "ORC_GDAL_BUILD_JOBS must be a positive integer." >&2; exit 2; }
echo "Installing compiler/build dependencies through Termux; system GDAL/OpenEXR are not replaced."
pkg install -y clang cmake ninja pkg-config proj libpng openjpeg json-c-static curl tar coreutils util-linux python
mkdir -p "$ORC_GDAL_ROOT" "$ORC_GDAL_CACHE_HOME/openroadcode/gdal" "$ORC_GDAL_STATE_HOME/openroadcode/gdal"
exec 9> "$ORC_GDAL_STATE_HOME/openroadcode/gdal/build.lock"
flock -n 9 || { echo "Another ORC GDAL build is running." >&2; exit 1; }
[[ ! -e "$ORC_GDAL_ROOT/current" || -L "$ORC_GDAL_ROOT/current" ]] || {
  echo "Refusing to replace a non-symlink current installation." >&2; exit 1;
}
archive="$ORC_GDAL_CACHE_HOME/openroadcode/gdal/gdal-$GDAL_VERSION.tar.xz"
if [[ ! -f "$archive" ]]; then
  curl --fail --location --retry 3 --connect-timeout 20 --max-time 900 \
    --continue-at - --output "$archive.part" \
    "https://download.osgeo.org/gdal/$GDAL_VERSION/gdal-$GDAL_VERSION.tar.xz"
  printf '%s  %s\n' "$GDAL_SHA256" "$archive.part" | sha256sum --check -
  mv -- "$archive.part" "$archive"
fi
printf '%s  %s\n' "$GDAL_SHA256" "$archive" | sha256sum --check -
source_root="$ORC_GDAL_STATE_HOME/openroadcode/gdal/source"
mkdir -p "$source_root"
if [[ ! -f "$source_root/gdal-$GDAL_VERSION/CMakeLists.txt" ]]; then
  tar -xf "$archive" -C "$source_root"
fi
candidate="$(mktemp -d "$ORC_GDAL_ROOT/gdal-$GDAL_VERSION.XXXXXX")"
build="$ORC_GDAL_STATE_HOME/openroadcode/gdal/build-$GDAL_VERSION"
log="$ORC_GDAL_STATE_HOME/openroadcode/gdal/build.log"
echo "Build log: $log"
echo "Candidate: $candidate (previous current installation remains active until verification passes)"
# Optional formats are off; explicitly keep GRIB and its PNG/JPEG2000 decoders.
# Internal TIFF/GeoTIFF/zlib avoid the unrelated system GDAL dependency graph.
cmake -S "$source_root/gdal-$GDAL_VERSION" -B "$build" -G Ninja \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG' \
  -DCMAKE_INSTALL_PREFIX="$candidate/runtime" -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_INSTALL_RPATH="\$ORIGIN/../lib;$PREFIX/lib" \
  -DBUILD_APPS=ON -DBUILD_TESTING=OFF -DBUILD_PYTHON_BINDINGS=OFF \
  -DBUILD_PYTHON_BINDINGS_OLD_VAL=OFF \
  -DHAVE_WFLAG_DOCUMENTATION_AND_NO_DEPRECATED=OFF \
  -DBUILD_JAVA_BINDINGS=OFF -DBUILD_CSHARP_BINDINGS=OFF \
  -DGDAL_BUILD_OPTIONAL_DRIVERS=OFF -DOGR_BUILD_OPTIONAL_DRIVERS=OFF \
  -DGDAL_ENABLE_PLUGINS=OFF -DGDAL_ENABLE_PLUGINS_NO_DEPS=OFF \
  -DGDAL_ENABLE_DRIVER_GRIB=ON -DGDAL_ENABLE_DRIVER_GTIFF=ON \
  -DGDAL_ENABLE_DRIVER_AAIGRID=ON -DGDAL_ENABLE_DRIVER_JP2OPENJPEG=ON \
  -DGDAL_USE_EXTERNAL_LIBS=OFF -DGDAL_USE_OPENEXR=OFF \
  -DGDAL_USE_OPENJPEG=ON -DGDAL_USE_PNG=ON \
  -DGDAL_USE_TIFF_INTERNAL=ON -DGDAL_USE_GEOTIFF_INTERNAL=ON \
  -DGDAL_USE_ZLIB_INTERNAL=ON -DGDAL_USE_JSONC_INTERNAL=ON \
  2>&1 | tee "$log"
cmake --build "$build" --parallel "$jobs" 2>&1 | tee -a "$log"
cmake --install "$build" 2>&1 | tee -a "$log"
mkdir -p "$candidate/bin"
for tool in gdalinfo gdal_translate gdalwarp; do
  cat > "$candidate/bin/$tool" <<'WRAPPER'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
runtime="$(cd -- "$(dirname -- "$(readlink -f -- "$0")")/../runtime" && pwd)"
export LD_LIBRARY_PATH="$runtime/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export GDAL_DATA="$runtime/share/gdal"
export GDAL_DRIVER_PATH=disable
exec "$runtime/bin/$(basename -- "$0")" "$@"
WRAPPER
  chmod 0755 "$candidate/bin/$tool"
done
verify "$candidate" 2>&1 | tee -a "$log"
link_tmp="$ORC_GDAL_ROOT/.current.new.$$"
ln -s -- "$candidate" "$link_tmp"
mv -Tf -- "$link_tmp" "$ORC_GDAL_ROOT/current"
link_tmp=''
echo "Isolated GDAL verified and activated: $ORC_GDAL_ROOT/current"
echo "Restart ORC, then select Forecast radar. No PATH or global library changes are needed."
