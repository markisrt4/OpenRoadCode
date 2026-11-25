#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
unset PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1
env_dir="$PWD/.venv-quality"
if [ ! -f "$env_dir/pyvenv.cfg" ]; then
    "${QUALITY_PYTHON:-python3}" -m venv "$env_dir"
fi
if ! grep -Eiq '^include-system-site-packages *= *false$' "$env_dir/pyvenv.cfg"; then
    echo "Quality environment must not inherit system packages." >&2
    exit 1
fi
if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then
    echo "Termux quality setup is not yet supported; use Ubuntu CI." >&2
    exit 1
fi
# Reuse portable feature dependencies without invoking runtime installers,
# hardware provisioning, or SDR region configuration.
source scripts/installers/installer_features.sh
packages=()
for feature in base desktop-ui web-ui gps automotive bluetooth; do
    while IFS= read -r package; do
        [[ -n "$package" ]] && packages+=("$package")
    done < <(get_feature_python_packages "$feature")
done
"$env_dir/bin/python" -m pip --isolated install -c constraints-quality-linux.txt -r requirements-dev.txt \
    "${packages[@]}" PyYAML scipy python-dateutil \
    'libmusicforge[analysis] @ git+https://github.com/markisrt4/libMusicForge.git@459baf6de7e76e0813999ea8ca2b6a8f928396ef' \
    'libsdrforge[zmq,audio] @ git+https://github.com/markisrt4/libSDRForge.git@55b0829e1a3b8d94f78a4e1f1ce9591d46c822f5'
"$env_dir/bin/python" -m pip check
"$env_dir/bin/ruff" --version
"$env_dir/bin/python" -m mypy --version
