#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
    pwd
)"

DEFAULT_NMEA_FILE="${SCRIPT_DIR}/data/romeo_to_warren_roundtrip_synthetic.nmea"

NMEA_FILE="${1:-${DEFAULT_NMEA_FILE}}"
GPSD_PORT="${GPSD_PORT:-2947}"
SENTENCE_DELAY="${GPS_EMULATOR_SENTENCE_DELAY:-5.0}"
SINGLE_SHOT="${GPS_EMULATOR_SINGLE_SHOT:-0}"

if ! command -v gpsfake >/dev/null 2>&1; then
    echo "gpsfake is not installed."
    echo "Install it with:"
    echo "  sudo apt install gpsd gpsd-clients python3-gps"
    exit 1
fi

if [[ ! -f "${NMEA_FILE}" ]]; then
    echo "NMEA source file not found:"
    echo "  ${NMEA_FILE}"
    exit 1
fi

if [[ ! -r "${NMEA_FILE}" ]]; then
    echo "NMEA source file is not readable:"
    echo "  ${NMEA_FILE}"
    exit 1
fi

if ss -ltn 2>/dev/null | grep -q ":${GPSD_PORT} "; then
    echo "TCP port ${GPSD_PORT} is already in use."
    echo
    echo "A system gpsd service or another emulator may already be running."
    echo "Check with:"
    echo "  gpspipe -w -n 5"
    exit 1
fi

GPSFAKE_ARGS=(
    --nowait
    --port "${GPSD_PORT}"
    --cycle "${SENTENCE_DELAY}"
)

if [[ "${SINGLE_SHOT}" == "1" ]]; then
    GPSFAKE_ARGS+=(--singleshot)
fi

echo "Starting GPS emulator"
echo "  source:         ${NMEA_FILE}"
echo "  gpsd endpoint:  127.0.0.1:${GPSD_PORT}"
echo "  sentence delay: ${SENTENCE_DELAY} seconds"
echo "  repeat route:   $([[ "${SINGLE_SHOT}" == "1" ]] && echo no || echo yes)"
echo
echo "Press Ctrl+C to stop the emulator."
echo

exec gpsfake "${GPSFAKE_ARGS[@]}" "${NMEA_FILE}"
