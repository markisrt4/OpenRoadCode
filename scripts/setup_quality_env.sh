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
constraints="$PWD/constraints-quality-linux.txt"
dev_requirements=(-r requirements-dev.txt)
if [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == */com.termux/files/usr ]]; then
    if [ ! -x "$PREFIX/bin/ruff" ]; then
        echo "Install native packages: pkg install python-numpy python-scipy python-pillow ruff" >&2
        exit 1
    fi
    dev_requirements=(pytest==9.2.0 mypy==2.4.1)
    ln -sfn "$PREFIX/bin/ruff" "$env_dir/bin/ruff"
    "$env_dir/bin/ruff" --version
    constraints="$(mktemp "${TMPDIR:-$PREFIX/tmp}/orc-constraints.XXXXXX")"
    trap 'rm -f "$constraints"' EXIT
    grep -Eiv '^(numpy|scipy|pillow|pyzmq|mypy|ruff|librt|mypy_extensions|pathspec)==' constraints-quality-linux.txt > "$constraints"
    "$env_dir/bin/python" - "$PREFIX/bin/python" "$constraints" <<'PY'
import importlib
import json
import pathlib
import subprocess
import sys
import sysconfig

native_python, constraints = sys.argv[1:]
native_info = json.loads(subprocess.check_output(
    [native_python, "-c", "import json, sys, sysconfig; print(json.dumps([list(sys.version_info[:2]), sysconfig.get_config_var('SOABI'), sysconfig.get_path('purelib')]))"],
    text=True,
))
if native_info[:2] != [list(sys.version_info[:2]), sysconfig.get_config_var("SOABI")]:
    raise SystemExit("Native Python ABI differs from quality environment; recreate with Termux Python.")
native_site = pathlib.Path(native_info[2])
site = pathlib.Path(sysconfig.get_path("purelib"))
sources = []
for name, module_name in (("numpy", "numpy"), ("scipy", "scipy"), ("pillow", "PIL"), ("pyzmq", "zmq")):
    metadata = list(native_site.glob(f"{name}-*.dist-info"))
    package = native_site / module_name
    if not package.is_dir() or len(metadata) != 1:
        raise SystemExit(f"Native {name} package or metadata missing; install it in Termux first.")
    sources.extend([package, *metadata, *native_site.glob(f"{name}.libs")])
for source in sources:
    target = site / source.name
    if target.exists() and not target.is_symlink():
        raise SystemExit(f"Existing package at {target}; recreate .venv-quality.")
for source in sources:
    target = site / source.name
    if target.is_symlink():
        target.unlink()
    target.symlink_to(source, target_is_directory=True)
with open(constraints, "a", encoding="utf-8") as output:
    for name, module_name in (("numpy", "numpy"), ("scipy", "scipy"), ("pillow", "PIL"), ("pyzmq", "zmq")):
        module = importlib.import_module(module_name)
        print(f"Using native {name} {module.__version__}")
        output.write(f"{name}=={module.__version__}\n")
PY
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
"$env_dir/bin/python" -m pip --isolated install -c "$constraints" "${dev_requirements[@]}" \
    "${packages[@]}" PyYAML scipy python-dateutil \
    'libmusicforge[analysis] @ git+https://github.com/markisrt4/libMusicForge.git@459baf6de7e76e0813999ea8ca2b6a8f928396ef' \
    'libsdrforge[zmq,audio] @ git+https://github.com/markisrt4/libSDRForge.git@ae29afdb073ba38193c723b8ab94f7d8271fddcf'
"$env_dir/bin/python" -m pip check
"$env_dir/bin/ruff" --version
"$env_dir/bin/python" -m mypy --version
