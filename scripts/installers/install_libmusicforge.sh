#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

# Install libMusicForge into the active OpenRoadCode Python environment.
# Prefer a compatible local checkout; otherwise use a verified public revision.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
LIBMUSICFORGE_SOURCE="${LIBMUSICFORGE_SOURCE:-}"
libmusicforge_python="${PYTHON:-python}"
# The upstream package has retained version 0.1.0 across incompatible revisions.
# Select by actual analysis support, not that version string.
default_musicforge_source="git+https://github.com/markisrt4/libMusicForge.git@7ca7cd444291ab02bea0e82df13bd05620634420"

compatible_local_analysis() {
  "$libmusicforge_python" - "$1" <<'PYTHON'
from pathlib import Path
import sys
import tomllib
root = Path(sys.argv[1])
try:
    project = tomllib.loads((root / "pyproject.toml").read_text())
    supported = bool(project.get("project", {}).get("optional-dependencies", {}).get("analysis"))
    supported = supported and (root / "src/musicforge/analysis/__init__.py").is_file()
except (OSError, ValueError):
    supported = False
raise SystemExit(0 if supported else 1)
PYTHON
}

if [[ -z "$LIBMUSICFORGE_SOURCE" ]]; then
  sibling_source="$PROJECT_ROOT/../libMusicForge"
  if [[ -f "$sibling_source/pyproject.toml" ]] && compatible_local_analysis "$sibling_source"; then
    LIBMUSICFORGE_SOURCE="$sibling_source"
  else
    if [[ -f "$sibling_source/pyproject.toml" ]]; then
      echo "[!] Skipping incompatible sibling libMusicForge: analysis module or extra is missing." >&2
    fi
    LIBMUSICFORGE_SOURCE="$default_musicforge_source"
  fi
elif [[ -d "$LIBMUSICFORGE_SOURCE" ]] && ! compatible_local_analysis "$LIBMUSICFORGE_SOURCE"; then
  echo "[!] Selected libMusicForge checkout lacks the analysis module or extra: $LIBMUSICFORGE_SOURCE" >&2
  echo "[!] Update that checkout, or select: LIBMUSICFORGE_SOURCE=$default_musicforge_source" >&2
  exit 1
fi

if [[ "${PREFIX:-}" == "/data/data/com.termux/files/usr" ]]; then
  # Termux provides a compatible NumPy through pkg install python-numpy.
  # Never ask pip to compile NumPy against Android's libc.
  "$libmusicforge_python" -c 'import numpy' || {
    echo "[!] Termux NumPy is unavailable. Install with: pkg install python-numpy" >&2
    echo "[!] The virtual environment must use --system-site-packages." >&2
    exit 1
  }
  echo "[*] Installing libMusicForge from $LIBMUSICFORGE_SOURCE (Termux system NumPy)..."
  "$libmusicforge_python" -m pip install --disable-pip-version-check httpx
  "$libmusicforge_python" -m pip install --disable-pip-version-check --force-reinstall --no-deps "$LIBMUSICFORGE_SOURCE"
else
  echo "[*] Installing libMusicForge with audio analysis from $LIBMUSICFORGE_SOURCE..."
  if [[ "$LIBMUSICFORGE_SOURCE" == git+* ]]; then
    # PEP 508 direct-reference syntax keeps extras separate from the VCS URL.
    "$libmusicforge_python" -m pip install --disable-pip-version-check --force-reinstall "libmusicforge[analysis] @ $LIBMUSICFORGE_SOURCE"
  else
    "$libmusicforge_python" -m pip install --disable-pip-version-check --force-reinstall "${LIBMUSICFORGE_SOURCE}[analysis]"
  fi
fi

"$libmusicforge_python" -c 'from musicforge.analysis import MusicAnalyzer, MusicAnalyzerIf, MusicAnalysisState, PercussionActivity; print("[+] libMusicForge analyzer:", MusicAnalyzer.__module__)'
