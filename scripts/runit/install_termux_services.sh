#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SERVICE_ROOT="${PREFIX:-/data/data/com.termux/files/usr}/var/service"

if ! command -v sv >/dev/null 2>&1; then
    echo "Termux runit services are not installed." >&2
    echo "Install them with: pkg install termux-services" >&2
    exit 1
fi

mkdir -p "$SERVICE_ROOT"

for service in openroadcode-broker openroadcode-navigation; do
    source_dir="$SCRIPT_DIR/$service"
    target="$SERVICE_ROOT/$service"

    if [[ ! -f "$source_dir/run" ]]; then
        echo "Missing runit service definition: $source_dir/run" >&2
        exit 1
    fi

    # The service directory must be real runtime state, not a symlink back into
    # the source tree. runsv creates supervise/ beneath this directory.
    if [[ -L "$target" ]]; then
        rm -f "$target"
    fi
    mkdir -p "$target"

    # Install the source definition and provide the checkout location through
    # the environment. This keeps mutable runit state out of the repository.
    sed \
        -e "s|^PROJECT_ROOT=.*$|PROJECT_ROOT=\"$PROJECT_ROOT\"|" \
        "$source_dir/run" > "$target/run"
    chmod +x "$target/run"

    echo "Installed $service -> $target"
done

echo
echo "OpenRoadCode Termux services installed."
echo "Start them with:"
echo "  sv up openroadcode-broker"
echo "  sv up openroadcode-navigation"
echo
echo "Check status with:"
echo "  sv status openroadcode-broker"
echo "  sv status openroadcode-navigation"
