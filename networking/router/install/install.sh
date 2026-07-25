#!/usr/bin/env bash
# Configure a Debian/Raspberry Pi OS system as a Wi-Fi access point using
# NetworkManager's shared IPv4 mode.
#
# Default LAN settings intentionally mirror common GL.iNet defaults:
#   Router address: 192.168.8.1/24
#   DHCP/NAT/DNS:    managed by NetworkManager

set -Eeuo pipefail

CONNECTION_NAME="openroad-bench-router"
SSID="OpenRoadCodeBench"
PASSWORD="openroadcode"
WIFI_IFACE=""
LAN_CIDR="192.168.8.1/24"
HOSTNAME_VALUE="openroad-router"
ASSUME_YES=0

usage() {
    cat <<'USAGE'
Usage:
  sudo ./install_pi3_router.sh [options]

Options:
  --ssid NAME               Wi-Fi network name
  --password PASSWORD       WPA2 password, minimum 8 characters
  --wifi-iface IFACE        Wireless interface, such as wlan0
  --connection-name NAME    NetworkManager connection name
  --lan-cidr CIDR           Router LAN address and prefix
                            Default: 192.168.8.1/24
  --hostname NAME           Hostname assigned to the Pi
  --yes                     Do not prompt before replacing the AP profile
  -h, --help                Show this help

Examples:
  sudo ./install_pi3_router.sh

  sudo ./install_pi3_router.sh \
      --ssid OpenRoadCodeBench \
      --password 'replace-this-password' \
      --wifi-iface wlan0

Notes:
  * NetworkManager provides DHCP, DNS forwarding, NAT, and firewall rules.
  * Internet access is shared from the system's current default route,
    normally Ethernet on a Pi 3/4/5.
  * Running this over SSH through the selected Wi-Fi interface will disconnect
    that SSH session when AP mode is enabled.
USAGE
}

log() {
    printf '[router-install] %s\n' "$*"
}

fatal() {
    printf '[router-install] ERROR: %s\n' "$*" >&2
    exit 1
}

require_root() {
    [[ ${EUID} -eq 0 ]] || fatal "Run this script with sudo."
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --ssid)
                [[ $# -ge 2 ]] || fatal "--ssid requires a value"
                SSID="$2"
                shift 2
                ;;
            --password)
                [[ $# -ge 2 ]] || fatal "--password requires a value"
                PASSWORD="$2"
                shift 2
                ;;
            --wifi-iface)
                [[ $# -ge 2 ]] || fatal "--wifi-iface requires a value"
                WIFI_IFACE="$2"
                shift 2
                ;;
            --connection-name)
                [[ $# -ge 2 ]] || fatal "--connection-name requires a value"
                CONNECTION_NAME="$2"
                shift 2
                ;;
            --lan-cidr)
                [[ $# -ge 2 ]] || fatal "--lan-cidr requires a value"
                LAN_CIDR="$2"
                shift 2
                ;;
            --hostname)
                [[ $# -ge 2 ]] || fatal "--hostname requires a value"
                HOSTNAME_VALUE="$2"
                shift 2
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
    [[ ${#PASSWORD} -ge 8 ]] || fatal "The Wi-Fi password must be at least 8 characters."
    [[ "$LAN_CIDR" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]{1,2}$ ]] \
        || fatal "Invalid --lan-cidr value: $LAN_CIDR"
    [[ -n "$SSID" ]] || fatal "SSID cannot be empty."
    [[ -n "$CONNECTION_NAME" ]] || fatal "Connection name cannot be empty."
}

install_packages() {
    log "Installing NetworkManager and Wi-Fi utilities..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y network-manager iw rfkill

    systemctl enable --now NetworkManager

    # Raspberry Pi OS releases predating Bookworm may still use dhcpcd.
    # It must not manage the same interface as NetworkManager.
    if systemctl list-unit-files dhcpcd.service >/dev/null 2>&1; then
        if systemctl is-enabled --quiet dhcpcd.service 2>/dev/null || \
           systemctl is-active --quiet dhcpcd.service 2>/dev/null; then
            log "Disabling dhcpcd to avoid fighting NetworkManager..."
            systemctl disable --now dhcpcd.service || true
        fi
    fi
}

detect_wifi_iface() {
    if [[ -n "$WIFI_IFACE" ]]; then
        [[ -d "/sys/class/net/$WIFI_IFACE/wireless" ]] \
            || fatal "$WIFI_IFACE is not a wireless network interface."
        return
    fi

    WIFI_IFACE="$(find /sys/class/net -mindepth 1 -maxdepth 1 -type l \
        -exec sh -c 'for p; do [[ -d "$p/wireless" ]] && basename "$p"; done' sh {} + \
        | head -n 1)"

    [[ -n "$WIFI_IFACE" ]] || fatal "No wireless interface was found."
}

verify_ap_support() {
    local phy
    phy="$(iw dev "$WIFI_IFACE" info 2>/dev/null | awk '/wiphy/ {print "phy" $2; exit}')"
    [[ -n "$phy" ]] || fatal "Could not determine the wireless PHY for $WIFI_IFACE."

    if ! iw phy "$phy" info | awk '
        /Supported interface modes:/ {inside=1; next}
        inside && /^\s*Band / {inside=0}
        inside && /\* AP$/ {found=1}
        END {exit(found ? 0 : 1)}
    '; then
        fatal "$WIFI_IFACE does not advertise Wi-Fi AP mode support."
    fi
}

confirm_changes() {
    (( ASSUME_YES == 1 )) && return

    cat <<EOF2

This will configure:
  Hostname:       $HOSTNAME_VALUE
  Wi-Fi device:   $WIFI_IFACE
  SSID:           $SSID
  Router address: $LAN_CIDR
  NM profile:     $CONNECTION_NAME

The selected Wi-Fi interface will stop acting as a client and become an AP.
EOF2

    read -r -p "Continue? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || fatal "Installation cancelled."
}

configure_hostname() {
    if [[ -n "$HOSTNAME_VALUE" ]]; then
        hostnamectl set-hostname "$HOSTNAME_VALUE"
    fi
}

configure_access_point() {
    log "Unblocking Wi-Fi..."
    rfkill unblock wifi || true
    nmcli radio wifi on

    log "Ensuring NetworkManager controls $WIFI_IFACE..."
    nmcli device set "$WIFI_IFACE" managed yes

    if nmcli -t -f NAME connection show | grep -Fxq "$CONNECTION_NAME"; then
        log "Removing existing profile: $CONNECTION_NAME"
        nmcli connection down "$CONNECTION_NAME" >/dev/null 2>&1 || true
        nmcli connection delete "$CONNECTION_NAME"
    fi

    log "Creating access-point profile..."
    nmcli connection add \
        type wifi \
        ifname "$WIFI_IFACE" \
        con-name "$CONNECTION_NAME" \
        autoconnect yes \
        ssid "$SSID"

    nmcli connection modify "$CONNECTION_NAME" \
        802-11-wireless.mode ap \
        802-11-wireless.band bg \
        802-11-wireless.channel 6 \
        802-11-wireless.powersave 2 \
        802-11-wireless-security.key-mgmt wpa-psk \
        802-11-wireless-security.psk "$PASSWORD" \
        ipv4.method shared \
        ipv4.addresses "$LAN_CIDR" \
        ipv4.never-default yes \
        ipv6.method disabled \
        connection.autoconnect yes \
        connection.autoconnect-priority 100

    log "Starting access point..."
    nmcli connection up "$CONNECTION_NAME"
}

print_summary() {
    local router_ip
    router_ip="${LAN_CIDR%/*}"

    cat <<EOF2

Router installation complete.

  SSID:             $SSID
  Password:         $PASSWORD
  Router address:   $router_ip
  Admin/SSH target: $router_ip
  Wi-Fi interface:  $WIFI_IFACE
  NM profile:       $CONNECTION_NAME

Useful commands:
  nmcli connection show --active
  nmcli device status
  ip -4 address show dev $WIFI_IFACE
  sudo nmcli connection down '$CONNECTION_NAME'
  sudo nmcli connection up '$CONNECTION_NAME'

NetworkManager shared mode supplies DHCP, DNS forwarding, NAT, and the
necessary forwarding/firewall rules. The upstream connection is whichever
interface currently owns the system default route, normally eth0.
EOF2
}

main() {
    require_root
    parse_args "$@"
    validate_settings
    install_packages
    detect_wifi_iface
    verify_ap_support
    confirm_changes
    configure_hostname
    configure_access_point
    print_summary
}

main "$@"
