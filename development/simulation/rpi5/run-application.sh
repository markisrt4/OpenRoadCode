#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
geometry="${1:-1280x720}"
case "$geometry" in 1280x720|800x480) ;; *) echo "Unsupported geometry: $geometry" >&2; exit 2 ;; esac
podman run --rm --platform linux/arm64 --network none --memory 768m --cpus 1 --cap-drop ALL --security-opt no-new-privileges -e LIBGL_ALWAYS_SOFTWARE=1 -e ORC_WAYDROID_PANEL=0 -e PYTHONDONTWRITEBYTECODE=1 -v "$root:/workspace:ro" -v "$root/config/runtime.simulated.toml:/workspace/config/runtime.toml:ro" localhost/orc-rpi5-application timeout -k 10s 300s bash /workspace/development/simulation/rpi5/start-display.sh "$geometry"
