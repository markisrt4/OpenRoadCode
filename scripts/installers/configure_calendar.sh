#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -eu
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
cd "$ROOT"
if [[ -n "${OPENROADCODE_PYTHON:-}" ]]; then
    PYTHON_BIN="$OPENROADCODE_PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/venv/bin/python"
else
    echo "Install the calendar feature using host_setup.sh first." >&2
    exit 1
fi
export OPENROADCODE_PYTHON="$PYTHON_BIN"
while true; do
    printf '\nOpenRoadCode Calendar Configuration\n'
    printf '%s\n' '1. List accounts' '2. Add account' '3. Enable account' \
        '4. Disable account' '5. Install synchronization service' \
        '6. Enable or restart synchronization' '7. Service status' \
        '8. Install Proton bridge service (requires Carbonate)' '0. Exit'
    read -r -p 'Select: ' choice || exit 0
    case "$choice" in
        1) "$PYTHON_BIN" -m controllers.calendar.configure_accounts list || true ;;
        2) "$PYTHON_BIN" -m controllers.calendar.configure_accounts add || true ;;
        3) "$PYTHON_BIN" -m controllers.calendar.configure_accounts enable || true ;;
        4) "$PYTHON_BIN" -m controllers.calendar.configure_accounts disable || true ;;
        5) sh development/calendar/install_linux_sync_service.sh --accounts || true ;;
        6) systemctl --user enable openroadcode-calendar-sync.service &&
            systemctl --user restart openroadcode-calendar-sync.service || true ;;
        7) systemctl --user --no-pager status openroadcode-calendar-sync.service || true ;;
        8) sh development/calendar/install_linux_systemd.sh || true ;;
        0) exit 0 ;;
        *) echo "Invalid selection" ;;
    esac
done
