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


def find_requested_suites(kinds: Sequence[str]) -> tuple[Path, ...]:
    """Return the unique test directories for all requested categories."""
    suites = {
        suite
        for kind in kinds
        for suite in find_suites(kind)
    }
    return tuple(sorted(suites))


def run_kinds(kinds: Sequence[str]) -> bool:
    """Run requested colocated suites together in one pytest process."""
    suites = find_requested_suites(kinds)
    if not suites:
        requested = ", ".join(kinds)
        print(f"ERROR: no {requested} test suites found", file=sys.stderr)
        return False

    relative_suites = tuple(suite.relative_to(PROJECT_ROOT) for suite in suites)
    labels = " + ".join(kinds)
    print(
        f"Running {len(relative_suites)} {labels} test suite(s) in one pytest session",
        flush=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *(str(suite) for suite in relative_suites),
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode in (0, PYTEST_NO_TESTS_COLLECTED)


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
    return 0 if run_kinds(kinds) else 1


if __name__ == "__main__":
    raise SystemExit(main())
