#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SOURCE="${LIBSDRFORGE_SOURCE:-}"
if [[ -z "$SOURCE" ]]; then
  if [[ -f "$PROJECT_ROOT/../libSDRForge/pyproject.toml" ]]; then
    SOURCE="$PROJECT_ROOT/../libSDRForge"
  else
    SOURCE="git+https://github.com/markisrt4/libSDRForge.git"
  fi
fi

if [[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]]; then
  python -c 'import numpy, scipy, zmq'
  python -m pip install --no-deps "$SOURCE"
elif [[ "$SOURCE" == git+* ]]; then
  python -m pip install "libsdrforge[zmq,audio] @ $SOURCE"
else
  python -m pip install "${SOURCE}[zmq,audio]"
fi
python -c 'import sdrforge, numpy, scipy, zmq; print("[+] SDRForge imports succeeded")'

# Both Linux and Termux installers use this entry point. Configure the
# independent SDRForge launchers before the next service startup.
bash "$PROJECT_ROOT/scripts/configure_sdrforge_region.sh" "${ORC_RADIO_LOCALE:-romeo}"
