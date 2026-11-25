#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""Run the scoped strict UI contract type gate with the current interpreter."""

import argparse
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


def is_quality_environment() -> bool:
    return Path(sys.prefix).resolve() == (ROOT / ".venv-quality").resolve()


def mypy_platform_args() -> list[str]:
    if is_termux() and is_quality_environment():
        return ["--no-native-parser", "--no-incremental"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--controllers",
        action="store_true",
        help="Check the entire controller layer using the existing strict configuration.",
    )
    options = parser.parse_args()
    if importlib.util.find_spec("mypy") is None:
        if is_termux() and not is_quality_environment() and not options.controllers:
            print("[SKIP] Strict UI types: mypy unavailable on Termux; Linux/CI still requires it")
            return 0
        print(
            "mypy is required: install with python -m pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return 1
    args = [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml"]
    # Keep incremental metadata isolated between the two strict scopes.
    cache_scope = "controllers" if options.controllers else "ui"
    args.extend(["--cache-dir", str(ROOT / ".mypy_cache" / cache_scope)])
    args.extend(mypy_platform_args())
    if options.controllers:
        args.append("controllers/")
    return subprocess.run(
        args,
        cwd=ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
