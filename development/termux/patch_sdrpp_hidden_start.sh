#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "Run this script from the normal Termux shell." >&2
  exit 2
}

proot-distro login debian --shared-tmp -- bash -s <<'DEBIAN'
set -euo pipefail

SDRPP_SRC="$HOME/SDRPlusPlus"
BACKEND="$SDRPP_SRC/core/backends/glfw/backend.cpp"
BUILD="$SDRPP_SRC/build"

[[ -f "$BACKEND" ]] || {
  echo "SDR++ GLFW backend not found: $BACKEND" >&2
  exit 1
}

python3 - "$BACKEND" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()

include_marker = '#include <filesystem>\n'
if '#include <cstdlib>\n' not in text:
    if include_marker not in text:
        raise SystemExit('Could not locate SDR++ include insertion point')
    text = text.replace(include_marker, include_marker + '#include <cstdlib>\n', 1)

# Apply the hint before every glfwCreateWindow attempt. GLFW_VISIBLE controls
# the initial X11 mapped state but still creates the native window, allowing
# ORC to discover/reparent it and explicitly map it inside its Tk host.
needle = '            // Create window with graphics context\n            monitor = glfwGetPrimaryMonitor();\n            window = glfwCreateWindow('
replacement = (
    '            // Create window with graphics context\n'
    '            monitor = glfwGetPrimaryMonitor();\n'
    '            const char* orcHidden = std::getenv("ORC_SDRPP_START_HIDDEN");\n'
    '            glfwWindowHint(GLFW_VISIBLE, (orcHidden && orcHidden[0] != \'\\0\') ? GLFW_FALSE : GLFW_TRUE);\n'
    '            window = glfwCreateWindow('
)

if 'ORC_SDRPP_START_HIDDEN' not in text:
    if needle not in text:
        raise SystemExit('Could not locate SDR++ GLFW window creation point')
    text = text.replace(needle, replacement, 1)

path.write_text(text)
PY

echo "[*] Rebuilding SDR++ with hidden embedded-start support"
cmake --build "$BUILD" --parallel "${BUILD_JOBS:-4}"

echo "[+] SDR++ hidden-start patch installed"
DEBIAN
