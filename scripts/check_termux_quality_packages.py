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
        metadata_name = f"{name}-{version}.dist-info".casefold()
        if not any(
            entry.name.casefold() == metadata_name and entry.is_symlink() and entry.is_dir()
            for entry in site.iterdir()
        ):
            continue
        module = importlib.import_module(module_name)
        if getattr(module, "__version__", None) == version:
            notices.add(f"{name} {version} is not supported on this platform")
    return notices


def check_packages() -> int:
    allowed = {notice.casefold() for notice in native_platform_notices()}
    result = subprocess.run(
        [sys.executable, "-m", "pip", "check"], capture_output=True, text=True, check=False
    )
    ignored = False
    unexpected = False
    for output, stream in ((result.stdout, sys.stdout), (result.stderr, sys.stderr)):
        for line in output.splitlines():
            notice = line.strip()
            if notice.casefold() in allowed:
                print(f"Using linked Termux build: {notice.split(' is not supported', 1)[0]}")
                ignored = True
            else:
                print(line, file=stream)
                unexpected = unexpected or bool(notice)
    if result.returncode == 1 and ignored and not unexpected:
        return 0
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(check_packages())
