#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
set -euo pipefail

# Exit 3 means no compatible release; all other failures are fatal.
[[ $# == 5 ]] || exit 2
version="$1"
image="$2"
root="$3"
skip_maplibre="$4"
skip_valhalla="$5"
[[ "$version" =~ ^[0-9a-f]{64}$ ]] || exit 2
case "$image" in
  debian:trixie) distro=debian13 ;;
  ubuntu:24.04) distro=ubuntu24.04 ;;
  *) exit 3 ;;
esac
case "$(uname -m)" in
  aarch64) arch=arm64 ;;
  x86_64) arch=amd64 ;;
  *) exit 3 ;;
esac
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
cd "$work"
asset="navigation-$distro-$arch.tar.gz"
base="https://github.com/markisrt4/OpenRoadCode/releases/download/navigation-$version"
status="$(curl -sSL --retry 3 --connect-timeout 20 -o SHA256SUMS -w '%{http_code}' "$base/SHA256SUMS")"
[[ "$status" != 404 ]] || exit 3
[[ "$status" == 200 ]] || exit 1
curl -fSL --retry 3 --connect-timeout 20 -o "$asset" "$base/$asset"
awk -v name="$asset" '$2 == name {print}' SHA256SUMS > expected
[[ "$(wc -l < expected)" == 1 ]]
sha256sum --strict -c expected
mkdir envelope stage
tar -xzf "$asset" -C envelope --no-same-owner --no-same-permissions
cd envelope
grep -Fx "component_version=$version" manifest.txt
grep -Fx "distribution=$distro" manifest.txt
grep -Fx "architecture=$arch" manifest.txt
grep -Fx "build_image=$image" manifest.txt
sha256sum --strict -c SHA256SUMS
shopt -s nullglob
archives=(orc-navigation-*.tar.gz)
[[ ${#archives[@]} == 1 ]]
tar -xzf "${archives[0]}" -C ../stage --no-same-owner --no-same-permissions
cd ../stage
# Validate before replacing any installed executable.
for binary in bin/openroadcode-map-renderer valhalla/bin/valhalla_service; do
  test -x "$binary"
  dependencies="$(LD_LIBRARY_PATH="$PWD/valhalla/lib" ldd "$binary")"
  printf '%s\n' "$dependencies"
  if grep -q 'not found' <<< "$dependencies"; then exit 1; fi
done
if (( ! skip_maplibre )); then
  sudo install -d "$root/bin"
  sudo install -m 0755 bin/openroadcode-map-renderer "$root/bin/openroadcode-map-renderer"
fi
if (( ! skip_valhalla )); then
  sudo install -d "$root/valhalla"
  sudo rsync -a --delete valhalla/ "$root/valhalla/"
  printf '%s\n' "$root/valhalla/lib" | sudo tee /etc/ld.so.conf.d/openroadcode-navigation.conf >/dev/null
  sudo ldconfig
fi
echo "[+] Installed navigation component $version ($distro/$arch)"
