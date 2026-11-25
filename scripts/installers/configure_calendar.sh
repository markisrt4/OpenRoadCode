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
if ! "$PYTHON_BIN" -c "import dateutil.rrule" >/dev/null 2>&1; then
    echo "Calendar recurrence support is missing from $PYTHON_BIN."
    read -r -p "Install python-dateutil into the OpenRoadCode environment? [Y/n] " answer
    if [[ "$answer" == [nN] ]]; then
        exit 1
    fi
    "$PYTHON_BIN" -m pip install python-dateutil
    "$PYTHON_BIN" -c "import dateutil.rrule"
fi
add_account() {
    printf '%s\n' '1. Proton Calendar' '2. Generic CalDAV' \
        '3. Nextcloud (CalDAV)' '4. iCloud (CalDAV)' '5. Fastmail (CalDAV)' '0. Back'
    read -r -p 'Calendar provider: ' provider || return 0
    case "$provider" in
        1)
            echo "Proton uses the unofficial Carbonate bridge."
            if systemctl --user is-active --quiet openroadcode-carbonate.service; then
                echo "Existing Proton bridge is running. Registering an ORC account without reauthentication."
                "$PYTHON_BIN" -m controllers.calendar.configure_accounts add --provider proton
                return $?
            fi
            if [[ -x "$HOME/.local/bin/carbonate" ]]; then
                export CARBONATE_BIN="$HOME/.local/bin/carbonate"
            elif [[ -x "$HOME/go/bin/carbonate" ]]; then
                export CARBONATE_BIN="$HOME/go/bin/carbonate"
            elif [[ -x "$HOME/src/carbonate/carbonate" ]]; then
                export CARBONATE_BIN="$HOME/src/carbonate/carbonate"
            elif ! command -v "${CARBONATE_BIN:-carbonate}" >/dev/null 2>&1; then
                read -r -p 'Download and build Carbonate from upstream main? [y/N] ' answer
                [[ "$answer" == [yY] ]] || return 1
                if ! command -v go >/dev/null 2>&1; then
                    sudo apt-get install -y golang-go || return 1
                fi
                mkdir -p "$HOME/.local/bin"
                local build_dir
                build_dir=$(mktemp -d "${TMPDIR:-$HOME}/orc-carbonate.XXXXXX") || return 1
                if ! git clone --depth 1 https://github.com/develonrails/carbonate.git "$build_dir" ||
                    ! (cd "$build_dir" && GOTOOLCHAIN=auto CGO_ENABLED=0 go build -o "$HOME/.local/bin/carbonate" ./cmd/carbonate); then
                    echo "Carbonate build failed. Source retained at $build_dir" >&2
                    return 1
                fi
                git -C "$build_dir" rev-parse HEAD
                export CARBONATE_BIN="$HOME/.local/bin/carbonate"
            fi
            read -r -p 'Authenticate Carbonate with Proton now? [y/N] ' answer
            if [[ "$answer" == [yY] ]]; then
                read -r -p 'Proton username: ' username
                "${CARBONATE_BIN:-carbonate}" auth "$username" || return 1
                "$PYTHON_BIN" -c 'from getpass import getpass; from security.environment_variable_secret_manager import EnvironmentVariableSecretManager; EnvironmentVariableSecretManager().set_secret("CARBONATE_BRIDGE_PASSWORD", getpass("Generated bridge password: "))' || return 1
            fi
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
account_menu() {
    while true; do
        printf '\nCalendar Account Management\n'
        printf '%s\n' '1. List accounts' '2. Add or register account' '3. Manage account status' \
            '4. Update account password' '5. Remove account' '0. Back'
        read -r -p 'Select: ' choice || return 0
        case "$choice" in
            1) "$PYTHON_BIN" -m controllers.calendar.configure_accounts list || true
                if systemctl --user is-active --quiet openroadcode-carbonate.service; then
                    echo "Proton bridge status: running."
                fi ;;
            2) add_account || true ;;
            3) "$PYTHON_BIN" -m controllers.calendar.configure_accounts status || true ;;
            4) "$PYTHON_BIN" -m controllers.calendar.configure_accounts password || true ;;
            5) "$PYTHON_BIN" -m controllers.calendar.configure_accounts remove || true ;;
            0) return 0 ;;
            *) echo "Invalid selection" ;;
        esac
    done
}
service_menu() {
    while true; do
        printf '\nCalendar Service Management\n'
        echo "Calendar sync downloads appointments into the local offline cache."
        echo "The Proton bridge connects to Proton; other providers do not require it."
        echo "These background services can run while the dashboard is closed."
        printf '%s\n' '1. Show service status' '2. Install or refresh sync service' \
            '3. Enable automatic sync and restart now' '4. Stop sync' \
            '5. Disable automatic sync and stop' '6. Show recent sync logs' '0. Back'
        read -r -p 'Select: ' choice || return 0
        case "$choice" in
            1) for unit in openroadcode-calendar-sync openroadcode-carbonate; do
                    systemctl --user --no-pager status "$unit.service" || true
                done ;;
            2) sh development/calendar/install_linux_sync_service.sh --accounts || true ;;
            3) sh development/calendar/install_linux_sync_service.sh --accounts &&
                systemctl --user enable openroadcode-calendar-sync.service &&
                systemctl --user restart openroadcode-calendar-sync.service || true ;;
            4) systemctl --user stop openroadcode-calendar-sync.service || true ;;
            5) systemctl --user disable --now openroadcode-calendar-sync.service || true ;;
            6) journalctl --user -u openroadcode-calendar-sync.service -n 30 --no-pager || true ;;
            0) return 0 ;;
            *) echo "Invalid selection" ;;
        esac
    done
}
while true; do
    printf '\nOpenRoadCode Calendar Configuration\n'
    printf '%s\n' '1. Account management' '2. Service management' '0. Exit'
    read -r -p 'Select: ' choice || exit 0
    case "$choice" in
        1) account_menu ;;
        2) service_menu ;;
        0) exit 0 ;;
        *) echo "Invalid selection" ;;
    esac
done
