#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""Run the scoped strict UI contract type gate with the current interpreter."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_termux() -> bool:
    return bool(os.environ.get("TERMUX_VERSION")) or os.environ.get("PREFIX", "").startswith(
        "/data/data/com.termux/"
    )


def mypy_platform_args() -> list[str]:
    if sys.platform == "android" or is_termux():
        return ["--no-native-parser", "--no-incremental"]
    return []


def main() -> int:
    if importlib.util.find_spec("mypy") is None:
        print(
            "mypy is required: install with python -m pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return 1
    args = [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml"]
    args.extend(mypy_platform_args())
    return subprocess.run(
        args,
        cwd=ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
