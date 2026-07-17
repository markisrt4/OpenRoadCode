#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PROJECT_ROOT}"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/venv}"
FEATURES_FILE="$SCRIPT_DIR/installer_features.sh"

if [[ ! -f "$FEATURES_FILE" ]]; then
  echo "[!] Feature definitions not found: $FEATURES_FILE" >&2
  exit 1
fi
# shellcheck disable=SC1091
source "$FEATURES_FILE"

if (( $# > 0 )); then
  FEATURES=("$@")
else
  mapfile -t FEATURES < <(get_feature_defaults)
fi

echo "[*] Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"

echo "[*] Installing Python packages..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools

python_packages=()
for feature in "${FEATURES[@]}"; do
  while read -r pkg; do
    [[ -z "$pkg" ]] && continue
    python_packages+=("$pkg")
  done < <(get_feature_python_packages "$feature")
done

unique_packages=()
for pkg in "${python_packages[@]}"; do
  if [[ " ${unique_packages[*]} " != *" $pkg "* ]]; then
    unique_packages+=("$pkg")
  fi
done

missing_python_packages=()
for pkg in "${unique_packages[@]}"; do
  if python -m pip show "$pkg" >/dev/null 2>&1; then
    echo "[*] Already installed in venv: $pkg"
  else
    missing_python_packages+=("$pkg")
  fi
done

if (( ${#missing_python_packages[@]} > 0 )); then
  echo "[*] Installing missing Python packages: ${missing_python_packages[*]}"
  python -m pip install --disable-pip-version-check "${missing_python_packages[@]}"
else
  echo "[*] All requested Python packages are already installed in the virtual environment."
fi

deactivate
