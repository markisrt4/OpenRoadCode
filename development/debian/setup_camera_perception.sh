#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

fail() {
    echo "Error: $*" >&2
    exit 1
}

if [[ "${EUID}" -eq 0 ]]; then
    fail "run this script as a normal user with sudo access, not as root"
fi

if ! command -v apt-get >/dev/null 2>&1; then
    fail "this setup script currently supports Debian/Ubuntu apt-based systems"
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
venv_python=""

if [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    venv_python="${VIRTUAL_ENV}/bin/python"
elif [[ -x "${repo_root}/venv/bin/python" ]]; then
    venv_python="${repo_root}/venv/bin/python"
fi

echo "OpenRoadCode camera/perception setup (Debian/Linux)"
echo "=================================================="
echo "Repository: ${repo_root}"
echo

sudo apt-get update
sudo apt-get install -y \
    python3-opencv \
    python3-pip \
    python3-venv \
    v4l-utils

if [[ -z "${venv_python}" ]]; then
    echo "No existing OpenRoadCode virtual environment found."
    echo "Creating: ${repo_root}/venv"
    python3 -m venv "${repo_root}/venv"
    venv_python="${repo_root}/venv/bin/python"
fi

"${venv_python}" -m pip install --upgrade pip
"${venv_python}" -m pip install --upgrade ultralytics

echo
"${venv_python}" - <<'PY'
import cv2
from ultralytics import YOLO

print(f"OpenCV: {cv2.__version__}")
print("Ultralytics import: OK")
print(f"YOLO class: {YOLO.__name__}")
PY

echo
if [[ -e /dev/video0 ]]; then
    echo "Camera device: /dev/video0 present"
else
    echo "Camera device: /dev/video0 not present"
    echo "This is fine on machines without the USB camera attached."
fi

echo
echo "Camera/perception setup complete."
echo "Activate the environment with:"
echo "  source ${repo_root}/venv/bin/activate"
echo
echo "Verify camera preview with:"
echo "  python -m hardware_io.camera.component_test.camera_preview"
echo
echo "Run YOLO perception preview with:"
echo "  python -m controllers.computer_vision.component_test.perception_preview"
