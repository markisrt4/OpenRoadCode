#!/usr/bin/env bash
set -euo pipefail
export DISPLAY=:99
echo "Starting Xvfb at ${1}..."
Xvfb "$DISPLAY" -screen 0 "${1}x24" -nolisten tcp -ac &
display_pid=$!
trap 'kill "$display_pid" 2>/dev/null || true' EXIT
for ((attempt=0; attempt<30; attempt++)); do
    kill -0 "$display_pid" || exit 1
    if timeout 3s xdpyinfo >/dev/null 2>&1; then
        echo "Virtual display ready"
        if [[ "${2:-}" == "--interactive" ]]; then
            cd /workspace
            export VENV_DIR=/opt/orc-venv PYTHONUNBUFFERED=1
            x11vnc -display "$DISPLAY" -localhost -rfbport 5900 -forever -shared -nopw >&2 &
            echo "Interactive display ready; VNC listening inside isolated container."
            shift 2
            bash runOrcUi --follow-logs "$@"
        else
            bash /workspace/development/simulation/rpi5/validate-application.sh
        fi
        exit
    fi
    echo "Waiting for Xvfb (attempt $((attempt+1))/30)"
    sleep 1
done
echo "Virtual display readiness timed out" >&2
exit 1
