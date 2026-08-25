#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE_NAME="${IMAGE_NAME:-openroadcode-valhalla-builder}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "Container engine not found: $CONTAINER_ENGINE" >&2
    exit 1
fi

resolve_base_image() {
    if [[ -n "${BASE_IMAGE:-}" ]]; then
        printf '%s\n' "$BASE_IMAGE"
        return
    fi

    if [[ ! -r /etc/os-release ]]; then
        echo "Cannot detect host OS; set BASE_IMAGE explicitly." >&2
        exit 1
    fi

    # shellcheck disable=SC1091
    source /etc/os-release
    case "${ID:-}" in
        ubuntu)
            printf 'ubuntu:%s\n' "${VERSION_ID:?Ubuntu VERSION_ID missing}"
            ;;
        debian)
            if [[ -n "${VERSION_CODENAME:-}" ]]; then
                printf 'debian:%s\n' "$VERSION_CODENAME"
            else
                printf 'debian:%s\n' "${VERSION_ID:?Debian version missing}"
            fi
            ;;
        raspbian)
            if [[ -n "${VERSION_CODENAME:-}" ]]; then
                printf 'debian:%s\n' "$VERSION_CODENAME"
            else
                printf 'debian:%s\n' "${VERSION_ID:?Raspbian version missing}"
            fi
            ;;
        *)
            echo "Unsupported host OS '${ID:-unknown}'; set BASE_IMAGE explicitly." >&2
            exit 1
            ;;
    esac
}

BASE_IMAGE="$(resolve_base_image)"

echo "Building $IMAGE_NAME using $CONTAINER_ENGINE"
echo "  host:  $(. /etc/os-release; printf '%s %s' "${ID:-unknown}" "${VERSION_ID:-unknown}")"
echo "  base:  $BASE_IMAGE"

"$CONTAINER_ENGINE" build \
    --build-arg "BASE_IMAGE=$BASE_IMAGE" \
    --tag "$IMAGE_NAME" \
    "$SCRIPT_DIR"
echo "Built container image: $IMAGE_NAME"
