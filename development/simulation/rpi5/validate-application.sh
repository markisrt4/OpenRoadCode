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
bash runOrcUi --follow-logs > >(tee "$log") 2>&1 &
pid=$!
for ((attempt=0; attempt<180; attempt++)); do
    kill -0 "$pid" 2>/dev/null || { echo "ORC exited during startup" >&2; exit 1; }
    if grep -q 'OpenRoadCode UI ready' "$log" && xdotool search --onlyvisible --pid "$pid" >/dev/null 2>&1; then
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
exit 1
