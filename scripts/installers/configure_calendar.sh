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
add_account() {
    printf '%s\n' '1. Proton Calendar' '2. Generic CalDAV' \
        '3. Nextcloud (CalDAV)' '4. iCloud (CalDAV)' '5. Fastmail (CalDAV)' '0. Back'
    read -r -p 'Calendar provider: ' provider || return 0
    case "$provider" in
        1)
            echo "Proton requires an installed and authenticated Carbonate bridge."
            read -r -p 'Install or refresh the bridge service and start it? [y/N] ' answer
            if [[ "$answer" == [yY] ]]; then
                sh development/calendar/install_linux_systemd.sh || return 1
                systemctl --user enable --now openroadcode-carbonate.service || return 1
            fi
            "$PYTHON_BIN" -m controllers.calendar.configure_accounts add --provider proton
            ;;
        2)
            "$PYTHON_BIN" -m controllers.calendar.configure_accounts add --provider caldav
            ;;
        3)
            echo "Use your Nextcloud server's DAV endpoint and an app password."
            "$PYTHON_BIN" -m controllers.calendar.configure_accounts add --provider caldav
            ;;
        4)
            echo "Use your Apple Account username and an app-specific password."
            "$PYTHON_BIN" -m controllers.calendar.configure_accounts add --provider caldav \
                --endpoint-default https://caldav.icloud.com/
            ;;
        5)
            echo "Use your Fastmail username and an app password with calendar access."
            "$PYTHON_BIN" -m controllers.calendar.configure_accounts add --provider caldav \
                --endpoint-default https://caldav.fastmail.com/dav/
            ;;
        0) return 0 ;;
        *) echo "Invalid provider"; return 1 ;;
    esac
}
while true; do
    printf '\nOpenRoadCode Calendar Configuration\n'
    printf '%s\n' '1. List accounts' '2. Add account' '3. Enable account' \
        '4. Disable account' '5. Install synchronization service' \
        '6. Enable or restart synchronization' '7. Service status' \
        '8. Update account password' '9. Remove account' '0. Exit'
    read -r -p 'Select: ' choice || exit 0
    case "$choice" in
        1) "$PYTHON_BIN" -m controllers.calendar.configure_accounts list || true ;;
        2) add_account || true ;;
        3) "$PYTHON_BIN" -m controllers.calendar.configure_accounts enable || true ;;
        4) "$PYTHON_BIN" -m controllers.calendar.configure_accounts disable || true ;;
        5) sh development/calendar/install_linux_sync_service.sh --accounts || true ;;
        6) sh development/calendar/install_linux_sync_service.sh --accounts &&
            systemctl --user enable openroadcode-calendar-sync.service &&
            systemctl --user restart openroadcode-calendar-sync.service || true ;;
        7) systemctl --user --no-pager status openroadcode-calendar-sync.service || true ;;
        8) "$PYTHON_BIN" -m controllers.calendar.configure_accounts password || true ;;
        9) "$PYTHON_BIN" -m controllers.calendar.configure_accounts remove || true ;;
        0) exit 0 ;;
        *) echo "Invalid selection" ;;
    esac
done
