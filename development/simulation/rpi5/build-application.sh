#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../../.." && pwd)"
context="$(mktemp -d)"
trap 'rm -rf -- "$context"' EXIT
cp "$here/Containerfile.application" "$context/Containerfile"
cp -R "$root/scripts/installers" "$context/installers"
podman build --platform linux/arm64 --memory 768m --cpu-period 100000 --cpu-quota 100000 -t localhost/orc-rpi5-application -f "$context/Containerfile" "$context"
