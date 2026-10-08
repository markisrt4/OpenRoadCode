#!/data/data/com.termux/files/usr/bin/bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

CORE_SERVICES=(
  openroadcode-message-broker
  openroadcode-valhalla
  openroadcode-navigation
  openroadcode-automotive
)

usage() {
  echo "Usage: $0 {start|stop|restart|status}" >&2
}

action="${1:-}"
case "$action" in
  start)
    for service in "${CORE_SERVICES[@]}"; do sv up "$service"; done
    ;;
  stop)
    for ((index=${#CORE_SERVICES[@]} - 1; index >= 0; index--)); do
      sv down "${CORE_SERVICES[$index]}"
    done
    ;;
  restart)
    "$0" stop
    "$0" start
    ;;
  status)
    for service in "${CORE_SERVICES[@]}"; do sv status "$service"; done
    ;;
  *)
    usage
    exit 2
    ;;
esac
