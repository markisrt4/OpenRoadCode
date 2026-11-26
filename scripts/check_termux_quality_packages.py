# SPDX-License-Identifier: MIT
"""Check dependencies while accepting Termux's ABI-verified native packages."""

from __future__ import annotations

import importlib
import importlib.metadata
import subprocess
import sys
import sysconfig
from pathlib import Path

TERMUX_NATIVE_MODULES = {"numpy": "numpy", "scipy": "scipy", "pillow": "PIL", "pyzmq": "zmq"}


def native_platform_notices() -> set[str]:
    """Allow only linked native distributions whose extension packages import."""
    site = Path(sysconfig.get_path("purelib"))
    notices = set()
    for name, module_name in TERMUX_NATIVE_MODULES.items():
        package = site / module_name
        if not package.is_symlink():
            continue
        version = importlib.metadata.version(name)
        metadata = site / f"{name}-{version}.dist-info"
        if not metadata.is_symlink() or not metadata.is_dir():
            continue
        module = importlib.import_module(module_name)
        if getattr(module, "__version__", None) == version:
            notices.add(f"{name} {version} is not supported on this platform")
    return notices


def check_packages() -> int:
    allowed = native_platform_notices()
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"], capture_output=True, text=True, check=False
    )
    ignored = False
    unexpected = False
    for line in result.stdout.splitlines():
        if line in allowed:
            print(f"Using linked Termux build: {line.split(' is not supported', 1)[0]}")
            ignored = True
        else:
            print(line)
            unexpected = unexpected or bool(line.strip())
    if result.stderr:
        sys.stderr.write(result.stderr)
    if result.returncode == 1 and ignored and not unexpected and not result.stderr.strip():
        return 0
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(check_packages())
