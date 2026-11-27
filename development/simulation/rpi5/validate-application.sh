#!/usr/bin/env bash
set -euo pipefail
cd /workspace
export VENV_DIR=/opt/orc-venv
log="$(mktemp)"
pid=""
cleanup() {
    if [[ -n "$pid" ]]; then
        kill "$pid" 2>/dev/null || true
        for ((i=0; i<5; i++)); do
            kill -0 "$pid" 2>/dev/null || break
            sleep 1
        done
        kill -KILL "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    fi
    echo "Application log saved during startup (shown live above)."
    rm -f "$log"
}
trap cleanup EXIT
export PYTHONUNBUFFERED=1
for module in tkinter numpy PIL zmq musicforge.analysis; do
    echo "Checking Python import: $module"
    timeout -k 5s 45s "$VENV_DIR/bin/python" -c "import $module"
    echo "Import passed: $module"
done
echo "Launching OpenRoadCode..."
# The isolated display has no window manager; Tk need not publish _NET_WM_PID.
visible_windows() {
    timeout 5s xdotool search --onlyvisible --name . 2>/dev/null || true
}
baseline="$(visible_windows)"
new_visible_window() {
    local window
    while read -r window; do
        [[ -n "$window" ]] || continue
        if ! grep -Fxq "$window" <<< "$baseline"; then
            echo "New visible window: $window"
            local info width height screen_width screen_height
            info="$(timeout 5s xwininfo -id "$window")" || return 1
            printf '%s\n' "$info"
            width="$(awk '/^  Width:/ {print $2}' <<< "$info")"
            height="$(awk '/^  Height:/ {print $2}' <<< "$info")"
            read -r screen_width screen_height < <(
                xdpyinfo | awk '/dimensions:/ {split($2, size, "x"); print size[1], size[2]}'
            )
            if [[ "$width" != "$screen_width" || "$height" != "$screen_height" ]]; then
                echo "Geometry mismatch: window ${width}x${height}, display ${screen_width}x${screen_height}" >&2
                return 1
            fi
            echo "Dashboard geometry matches display: ${width}x${height}"
            return 0
        fi
    done < <(visible_windows)
    return 1
}
bash runOrcUi --follow-logs > >(tee "$log") 2>&1 &
pid=$!
for ((attempt=0; attempt<180; attempt++)); do
    kill -0 "$pid" 2>/dev/null || { echo "ORC exited during startup" >&2; exit 1; }
    if grep -q 'OpenRoadCode UI ready' "$log" && new_visible_window; then
        sleep 5
        kill -0 "$pid"
        if grep -Eq 'Traceback \(most recent call last\)|Exception in Tkinter callback' "$log"; then
            echo "ORC reported a runtime exception" >&2
            exit 1
        fi
        echo "ORC startup and visible window check passed"
        exit 0
    fi
    if (( attempt % 10 == 0 )); then
        echo "Waiting for ORC readiness (attempt $((attempt+1))/180)"
    fi
    sleep 1
done
echo "Timed out waiting for ORC readiness and visible window" >&2
timeout 5s xwininfo -root -tree || true
exit 1
