#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""Run the scoped strict UI contract type gate with the current interpreter."""

import importlib.util
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if importlib.util.find_spec("mypy") is None:
        print("mypy is required: install with python -m pip install -r requirements-dev.txt",
              file=sys.stderr)
        return 1
    return subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml"],
        cwd=ROOT, check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
