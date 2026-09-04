#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SERVICE_ROOT="${PREFIX:-/data/data/com.termux/files/usr}/var/service"
SERVICES=(
    openroadcode-service-manager
    openroadcode-message-broker
    openroadcode-navigation
    openroadcode-automotive
    openroadcode-adsb
)
LEGACY_SERVICES=(openroadcode-broker)

if ! command -v sv >/dev/null 2>&1; then
    echo "Termux runit services are not installed." >&2
    echo "Install them with: pkg install termux-services" >&2
    exit 1
fi

mkdir -p "$SERVICE_ROOT"

# Remove service names retired by the version-controlled definitions. Stop the
# old instance first so migration cannot leave two brokers bound to the same
# ZeroMQ ports.
for service in "${LEGACY_SERVICES[@]}"; do
    target="$SERVICE_ROOT/$service"
    if [[ -e "$target" || -L "$target" ]]; then
        sv down "$service" >/dev/null 2>&1 || true
        rm -rf "$target"
        echo "Removed legacy service $service"
    fi
done

for service in "${SERVICES[@]}"; do
    source_dir="$SCRIPT_DIR/$service"
    target="$SERVICE_ROOT/$service"

    if [[ ! -f "$source_dir/run" ]]; then
        echo "Missing runit service definition: $source_dir/run" >&2
        exit 1
    fi

    # The service directory must be real runtime state, not a symlink back into
    # the source tree. runsv creates supervise/ beneath this directory.
    if [[ -L "$target" ]]; then
        sv down "$service" >/dev/null 2>&1 || true
        rm -f "$target"
    elif [[ -e "$target" && ! -d "$target" ]]; then
        echo "Service target exists and is not a directory: $target" >&2
        exit 1
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

# runsvdir normally notices new service directories immediately. If the Termux
# service environment predates a newly installed definition, wait briefly for
# adoption and explain the recovery instead of letting `sv` emit the rather
# cryptic "supervise/ok" warning.
echo
echo "Verifying runit supervision..."
unsupervised=()
for service in "${SERVICES[@]}"; do
    target="$SERVICE_ROOT/$service"
    for _ in 1 2 3 4 5; do
        [[ -e "$target/supervise/ok" ]] && break
        sleep 0.2
    done
    if [[ -e "$target/supervise/ok" ]]; then
        echo "  supervised: $service"
    else
        echo "  waiting:    $service"
        unsupervised+=("$service")
    fi
done

if (( ${#unsupervised[@]} > 0 )); then
    echo >&2
    echo "Some newly installed services have not been adopted by runsvdir yet." >&2
    echo "Restart the Termux service supervisor, then reopen Termux:" >&2
    echo "  pkill runsvdir" >&2
    echo >&2
    echo "After reopening Termux, verify with:" >&2
    for service in "${unsupervised[@]}"; do
        echo "  sv status $service" >&2
    done
fi

echo
echo "OpenRoadCode Termux services installed."
echo "The service manager stays available as the lightweight local control plane."
echo "Start the core stack with:"
echo "  sv up openroadcode-message-broker"
echo "  sv up openroadcode-navigation"
echo "  sv up openroadcode-automotive"
echo "Optional ADS-B:"
echo "  sv up openroadcode-adsb"
echo
echo "Check status with:"
for service in "${SERVICES[@]}"; do
    echo "  sv status $service"
done
