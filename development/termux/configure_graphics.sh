#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

set -euo pipefail

[[ "${PREFIX:-}" == /data/data/com.termux/files/usr* ]] || {
  echo "This graphics helper must run inside Termux." >&2
  exit 2
}

INSTALL=0
if [[ "${1:-}" == "--install" ]]; then
  INSTALL=1
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--install]" >&2
  exit 2
fi

hardware="$(getprop ro.hardware 2>/dev/null || true)"
platform="$(getprop ro.board.platform 2>/dev/null || true)"
kgsl_device="/dev/kgsl-3d0"

package_available() {
  apt-cache show "$1" >/dev/null 2>&1
}

is_qualcomm=0
if [[ "$hardware" == qcom* || "$platform" == qcom* || -e "$kgsl_device" ]]; then
  is_qualcomm=1
fi

packages=(mesa mesa-dev vulkan-loader-generic)
graphics_backend="generic"

if [[ "$is_qualcomm" == 1 ]] && package_available mesa-vulkan-icd-freedreno; then
  packages+=(mesa-vulkan-icd-freedreno)
  graphics_backend="freedreno-zink"
fi

if [[ "$INSTALL" == 1 ]]; then
  echo "[*] Installing Termux graphics packages for backend: $graphics_backend"
  pkg install -y "${packages[@]}"
fi

cat <<EOF
Termux graphics detection
  ro.hardware:       ${hardware:-unknown}
  ro.board.platform: ${platform:-unknown}
  KGSL device:       $([[ -e "$kgsl_device" ]] && echo present || echo absent)
  selected backend:  $graphics_backend
EOF

if [[ "$graphics_backend" == "freedreno-zink" ]]; then
  cat <<'EOF'

Recommended runtime environment for OpenGL applications:
  export MESA_LOADER_DRIVER_OVERRIDE=zink
EOF
else
  cat <<'EOF'

No vendor-specific Mesa Vulkan ICD was selected automatically.
Leave MESA_LOADER_DRIVER_OVERRIDE unset unless a working hardware backend has
been validated on this device. OpenRoadCode should continue to function with a
software/basic graphics path when hardware acceleration is unavailable.
EOF
fi

echo
if command -v vulkaninfo >/dev/null 2>&1; then
  echo "Vulkan probe available: vulkaninfo --summary"
else
  echo "Vulkan probe unavailable: install vulkan-tools to enable it"
fi

if command -v glxinfo >/dev/null 2>&1; then
  if [[ "$graphics_backend" == "freedreno-zink" ]]; then
    echo "OpenGL probe: MESA_LOADER_DRIVER_OVERRIDE=zink glxinfo -B"
  else
    echo "OpenGL probe: glxinfo -B"
  fi
else
  echo "OpenGL probe unavailable: install mesa-demos to enable it"
fi
