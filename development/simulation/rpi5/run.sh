#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
podman run --rm --platform linux/arm64 --network none --memory 768m --cpus 1 --cap-drop ALL --security-opt no-new-privileges -v "$root:/workspace:ro" localhost/orc-rpi5-sim bash /workspace/development/simulation/rpi5/validate.sh
