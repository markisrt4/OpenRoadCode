#!/usr/bin/env bash
# Remove the NetworkManager Wi-Fi access-point profile created by
# install_pi3_router.sh.
#
# By default, this script removes only the router connection profile. It does
# not remove NetworkManager or other packages because they may be managing the
# system's Ethernet or other network connections.

set -Eeuo pipefail

CONNECTION_NAME="openroad-bench-router"
WIFI_IFACE=""
NEW_HOSTNAME=""
ENABLE_DHCPCD=0
PURGE_PACKAGES=0
ASSUME_YES=0

usage() {
    cat <<'USAGE'
Usage:
  sudo ./uninstall_pi3_router.sh [options]

Options:
  --connection-name NAME    NetworkManager AP profile to remove
                            Default: openroad-bench-router
  --wifi-iface IFACE        Wireless interface to disconnect, such as wlan0
  --hostname NAME           Set a replacement hostname after removal
  --enable-dhcpcd           Re-enable dhcpcd.service when it is installed
  --purge-packages          Remove NetworkManager, iw, and rfkill packages
                            Use cautiously; this may disrupt other networking
  --yes                     Do not prompt for confirmation
  -h, --help                Show this help

Examples:
  sudo ./uninstall_pi3_router.sh

  sudo ./uninstall_pi3_router.sh \
      --connection-name openroad-bench-router \
      --wifi-iface wlan0 \
      --hostname raspberrypi

Notes:
  * The installer did not record the Pi's previous hostname, so hostname
    restoration must be requested explicitly with --hostname.
  * Package removal is intentionally optional. NetworkManager may also manage
    Ethernet or unrelated Wi-Fi profiles.
USAGE
}

log() {
    printf '[router-uninstall] %s\n' "$*"
}

warn() {
    printf '[router-uninstall] WARNING: %s\n' "$*" >&2
}

fatal() {
    printf '[router-uninstall] ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    [[ ${EUID} -eq 0 ]] || fatal "Run this script with sudo."
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --connection-name)
                [[ $# -ge 2 ]] || fatal "--connection-name requires a value"
                CONNECTION_NAME="$2"
                shift 2
                ;;
            --wifi-iface)
                [[ $# -ge 2 ]] || fatal "--wifi-iface requires a value"
                WIFI_IFACE="$2"
                shift 2
                ;;
            --hostname)
                [[ $# -ge 2 ]] || fatal "--hostname requires a value"
                NEW_HOSTNAME="$2"
                shift 2
                ;;
            --enable-dhcpcd)
                ENABLE_DHCPCD=1
                shift
                ;;
            --purge-packages)
                PURGE_PACKAGES=1
                shift
                ;;
            --yes)
                ASSUME_YES=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                fatal "Unknown argument: $1"
                ;;
        esac
    done
}

validate_settings() {
    [[ -n "$CONNECTION_NAME" ]] || fatal "Connection name cannot be empty."

    if [[ -n "$WIFI_IFACE" && ! -d "/sys/class/net/$WIFI_IFACE" ]]; then
        fatal "Network interface does not exist: $WIFI_IFACE"
    fi
}

confirm_changes() {
    (( ASSUME_YES == 1 )) && return

    cat <<EOF2

This will remove:
  NetworkManager profile: $CONNECTION_NAME

Additional actions:
  Wi-Fi interface:        ${WIFI_IFACE:-auto-detect from profile}
  Replacement hostname:  ${NEW_HOSTNAME:-unchanged}
  Re-enable dhcpcd:       $([[ $ENABLE_DHCPCD -eq 1 ]] && echo yes || echo no)
  Purge packages:         $([[ $PURGE_PACKAGES -eq 1 ]] && echo yes || echo no)
EOF2

    if (( PURGE_PACKAGES == 1 )); then
        warn "Purging NetworkManager may disconnect Ethernet and SSH sessions."
    fi

    read -r -p "Continue? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || fatal "Uninstallation cancelled."
}

find_profile_interface() {
    [[ -n "$WIFI_IFACE" ]] && return

    if command -v nmcli >/dev/null 2>&1 && \
       nmcli -t -f NAME connection show | grep -Fxq "$CONNECTION_NAME"; then
        WIFI_IFACE="$(nmcli -g connection.interface-name connection show "$CONNECTION_NAME" 2>/dev/null || true)"
    fi
}

remove_access_point_profile() {
    if ! command -v nmcli >/dev/null 2>&1; then
        warn "nmcli is unavailable; the NetworkManager profile cannot be removed automatically."
        return
    fi

    if nmcli -t -f NAME connection show | grep -Fxq "$CONNECTION_NAME"; then
        log "Stopping access-point profile: $CONNECTION_NAME"
        nmcli connection down "$CONNECTION_NAME" >/dev/null 2>&1 || true

        log "Deleting access-point profile: $CONNECTION_NAME"
        nmcli connection delete "$CONNECTION_NAME"
    else
        log "Profile '$CONNECTION_NAME' is not present; nothing to delete."
    fi

    if [[ -n "$WIFI_IFACE" && -d "/sys/class/net/$WIFI_IFACE" ]]; then
        log "Disconnecting $WIFI_IFACE from any remaining active connection..."
        nmcli device disconnect "$WIFI_IFACE" >/dev/null 2>&1 || true
        nmcli radio wifi on >/dev/null 2>&1 || true
    fi
}

restore_hostname() {
    [[ -n "$NEW_HOSTNAME" ]] || return
    log "Setting hostname to: $NEW_HOSTNAME"
    hostnamectl set-hostname "$NEW_HOSTNAME"
}

restore_dhcpcd() {
    (( ENABLE_DHCPCD == 1 )) || return

    if systemctl list-unit-files dhcpcd.service >/dev/null 2>&1; then
        log "Enabling dhcpcd.service..."
        systemctl enable --now dhcpcd.service
    else
        warn "dhcpcd.service is not installed."
    fi
}

purge_router_packages() {
    (( PURGE_PACKAGES == 1 )) || return

    log "Removing NetworkManager and Wi-Fi utility packages..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get remove --purge -y network-manager iw rfkill
    apt-get autoremove -y
}

print_summary() {
    cat <<EOF2

Router profile removal complete.

  Removed profile:       $CONNECTION_NAME
  Wi-Fi interface:       ${WIFI_IFACE:-not determined}
  Current hostname:      $(hostname)
  dhcpcd requested:      $([[ $ENABLE_DHCPCD -eq 1 ]] && echo yes || echo no)
  Packages purged:       $([[ $PURGE_PACKAGES -eq 1 ]] && echo yes || echo no)

The 192.168.8.1/24 address, DHCP service, DNS forwarding, NAT, and firewall
rules supplied by NetworkManager shared mode disappear with the deleted AP
profile. Other NetworkManager connection profiles are left intact unless the
packages were explicitly purged.
EOF2
}

main() {
    require_root
    parse_args "$@"
    validate_settings
    confirm_changes
    find_profile_interface
    remove_access_point_profile
    restore_hostname
    restore_dhcpcd
    purge_router_packages
    print_summary
}

main "$@"
