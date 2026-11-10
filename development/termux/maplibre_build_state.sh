#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

# MapLibre compiles libpng's header version into its decoder. Termux package
# upgrades can invalidate that decoder even when the installed binary exists.
maplibre_build_signature() {
  local png_version
  png_version="$(pkg-config --modversion libpng)" || return
  printf 'maplibre=%s\nlibpng=%s\n' "$MAPLIBRE_REF" "$png_version"
  sha256sum "$PREFIX/include/png.h" "$PREFIX/include/pngconf.h"
}

maplibre_needs_build() {
  local artifact="$1" build_dir="$2" stamp="$3" signature="$4"
  [[ "$FORCE_REBUILD" == "1" || ! -e "$artifact" ||
     ! -f "$build_dir/CMakeCache.txt" || ! -f "$stamp" ]] && return 0
  [[ "$(cat "$stamp")" != "$signature" ]]
}
