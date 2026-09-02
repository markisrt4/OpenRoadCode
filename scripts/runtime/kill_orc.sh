#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

# Emergency cleanup for interactive OpenRoadCode UI processes. This intentionally
# does not stop supervised broker/navigation/ADS-B services.
PATTERN='python(3)? .* -m apps\.orcUi|python(3)? -m apps\.orcUi|openroadcode-map-renderer|development/termux/start_map_renderer\.sh'
SELF_PID="$$"
PARENT_PID="${PPID:-0}"

find_pids() {
    pgrep -f "$PATTERN" 2>/dev/null | while read -r pid; do
        [[ "$pid" == "$SELF_PID" || "$pid" == "$PARENT_PID" ]] && continue
        printf '%s\n' "$pid"
    done
}

mapfile -t pids < <(find_pids)
if ((${#pids[@]} == 0)); then
    echo "No ORC UI/map renderer processes found."
    exit 0
fi

echo "Stopping ORC UI/map renderer processes: ${pids[*]}"
kill -TERM "${pids[@]}" 2>/dev/null || true

for _ in 1 2 3 4 5 6 7 8 9 10; do
    sleep 0.2
    mapfile -t remaining < <(find_pids)
    ((${#remaining[@]} == 0)) && {
        echo "ORC UI/map renderer stopped."
        exit 0
    }
done

mapfile -t remaining < <(find_pids)
if ((${#remaining[@]} > 0)); then
    echo "Force-killing remaining processes: ${remaining[*]}"
    kill -KILL "${remaining[@]}" 2>/dev/null || true
fi

echo "ORC UI/map renderer stopped."
