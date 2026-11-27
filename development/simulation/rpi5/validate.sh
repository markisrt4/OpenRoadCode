#!/usr/bin/env bash
set -euo pipefail
cd /workspace
fixture="$PWD/development/simulation/rpi5/fixtures"
test "$(uname -m)" = aarch64
test "$(dpkg --print-architecture)" = arm64
export OPENROAD_RPI_MODEL_FILE="$fixture/device-tree-model"
export OPENROAD_OS_RELEASE_FILE="$fixture/os-release"
plan="$(bash scripts/installers/host_setup.sh --target rpi5 --feature navigation --feature cesium --feature waydroid --show-plan)"
printf '%s\n' "$plan"
grep -Eq 'Detected target: +rpi5$' <<< "$plan"
grep -Eq 'Detected architecture: +arm64$' <<< "$plan"
grep -Eq 'Features:.*waydroid' <<< "$plan"
grep -Eq 'Features:.*android-integration' <<< "$plan"
grep -Eq 'Features:.*browser' <<< "$plan"
for geometry in 1280x720 800x480; do
    xvfb-run -a -s "-screen 0 ${geometry}x24" python3 - "$geometry" <<'PY'
import sys
import tkinter as tk

root = tk.Tk()
try:
    expected = tuple(map(int, sys.argv[1].split("x")))
    assert (root.winfo_screenwidth(), root.winfo_screenheight()) == expected
    root.update()
    print(f"Tk display smoke test passed: {sys.argv[1]}")
finally:
    root.destroy()
PY
done
echo "Pi 5 simulation smoke checks passed."
