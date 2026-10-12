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
    return bool(os.environ.get('TERMUX_VERSION')) or os.environ.get('PREFIX','').startswith('/data/data/com.termux/')


def main() -> int:
    if importlib.util.find_spec("mypy") is None:
        if is_termux():
            print('[SKIP] Strict UI types: mypy unavailable on Termux; Linux/CI still requires it')
            return 0
        print("mypy is required: install with python -m pip install -r requirements-dev.txt",
              file=sys.stderr)
        return 1
    return subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml"],
        cwd=ROOT, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
