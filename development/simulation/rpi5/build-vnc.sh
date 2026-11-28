#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
podman build --platform linux/arm64 --memory 768m --cpu-period 100000 --cpu-quota 100000 -t localhost/orc-rpi5-vnc -f "$here/Containerfile.vnc" "$here"
