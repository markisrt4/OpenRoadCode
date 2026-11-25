#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SOURCE="${LIBSDRFORGE_SOURCE:-git+https://github.com/markisrt4/libSDRForge.git@b13bfe105e7cb4eae2f7b2a41a6e39f6c841e667}"

if [[ "${PREFIX:-}" == /data/data/com.termux/files/usr ]]; then
  python -c 'import numpy, scipy, zmq'
  python -m pip install --no-deps "$SOURCE"
elif [[ "$SOURCE" == git+* ]]; then
  python -m pip install "libsdrforge[zmq,audio] @ $SOURCE"
else
  python -m pip install "${SOURCE}[zmq,audio]"
fi
python -c 'import sdrforge, numpy, scipy, zmq; from sdrforge.live_transport_server import main; print("[+] SDRForge imports succeeded")'

# Both Linux and Termux installers use this entry point. Configure the
# independent SDRForge launchers before the next service startup.
if [[ -n "${ORC_RADIO_LOCALE:-}" || ! -f "${XDG_CONFIG_HOME:-$HOME/.config}/sdrforge/radio-region.conf" ]]; then
  bash "$PROJECT_ROOT/scripts/configure_sdrforge_region.sh" "${ORC_RADIO_LOCALE:-romeo}"
fi
