#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run colocated OpenRoadCode automated test suites."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUITE_DIRECTORIES = {
    "unit": "unit_test",
    "integration": "integration_test",
}
PYTEST_NO_TESTS_COLLECTED = 5


def find_suites(kind: str) -> tuple[Path, ...]:
    """Return directories containing automated tests of the requested kind."""
    directory_name = SUITE_DIRECTORIES[kind]
    suites = {
        test_file.parent
        for test_file in PROJECT_ROOT.rglob(
            f"{directory_name}/test_*.py"
        )
        if ".git" not in test_file.parts
    }
    return tuple(sorted(suites))


def run_kind(kind: str) -> bool:
    """Run every colocated suite of one kind and report whether all passed."""
    suites = find_suites(kind)
    if not suites:
        print(f"ERROR: no {kind} test suites found", file=sys.stderr)
        return False

    print(f"Running {len(suites)} {kind} test suite(s)", flush=True)
    for suite in suites:
        relative_suite = suite.relative_to(PROJECT_ROOT)
        print(f"\n==> {relative_suite}", flush=True)
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                str(relative_suite),
            ],
            cwd=PROJECT_ROOT,
            check=False,
        )
        if result.returncode not in (0, PYTEST_NO_TESTS_COLLECTED):
            return False

    return True


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "suite",
        choices=("unit", "integration", "all"),
        help="Automated test category to run",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    kinds = (
        tuple(SUITE_DIRECTORIES)
        if args.suite == "all"
        else (args.suite,)
    )

    for kind in kinds:
        if not run_kind(kind):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
