#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

# Install libMusicForge into the active OpenRoadCode Python environment.
# Prefer a local checkout for development; otherwise use the public Git repo.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
LIBMUSICFORGE_SOURCE="${LIBMUSICFORGE_SOURCE:-}"
if [[ -z "$LIBMUSICFORGE_SOURCE" ]]; then
  if [[ -f "$PROJECT_ROOT/../libMusicForge/pyproject.toml" ]]; then
    LIBMUSICFORGE_SOURCE="$PROJECT_ROOT/../libMusicForge"
  else
    LIBMUSICFORGE_SOURCE="git+https://github.com/markisrt4/libMusicForge.git"
  fi
fi

if [[ "${PREFIX:-}" == "/data/data/com.termux/files/usr" ]]; then
  # Termux provides a compatible NumPy through pkg install python-numpy.
  # Never ask pip to compile NumPy against Android's libc.
  python -c 'import numpy' || {
    echo "[!] Termux NumPy is unavailable. Install with: pkg install python-numpy" >&2
    echo "[!] The virtual environment must use --system-site-packages." >&2
    exit 1
  }
  echo "[*] Installing libMusicForge from $LIBMUSICFORGE_SOURCE (Termux system NumPy)..."
  python -m pip install --disable-pip-version-check httpx
  python -m pip install --disable-pip-version-check --no-deps "$LIBMUSICFORGE_SOURCE"
else
  echo "[*] Installing libMusicForge with audio analysis from $LIBMUSICFORGE_SOURCE..."
  python -m pip install --disable-pip-version-check "${LIBMUSICFORGE_SOURCE}[analysis]"
fi

python -c 'from musicforge.analysis import MusicAnalyzer; print("[+] libMusicForge analyzer:", MusicAnalyzer.__module__)'
