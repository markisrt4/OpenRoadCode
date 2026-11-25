#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""Run the scoped strict UI contract type gate with the current interpreter."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def is_termux() -> bool:
    return bool(os.environ.get("TERMUX_VERSION")) or os.environ.get("PREFIX", "").startswith(
        "/data/data/com.termux/"
    )


def is_quality_environment() -> bool:
    return Path(sys.prefix).resolve() == (ROOT / ".venv-quality").resolve()


def mypy_platform_args() -> list[str]:
    if is_termux() and is_quality_environment():
        return ["--no-native-parser", "--no-incremental"]
    return []


def main() -> int:
    if importlib.util.find_spec("mypy") is None:
        if is_termux() and not is_quality_environment():
            print("[SKIP] Strict UI types: mypy unavailable on Termux; Linux/CI still requires it")
            return 0
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
