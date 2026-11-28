#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Run colocated OpenRoadCode automated test suites."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
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
        for test_file in PROJECT_ROOT.rglob(f"{directory_name}/test_*.py")
        if not any(
            part in {".git", ".venv", "venv", "build"} or part.startswith(".venv-")
            for part in test_file.relative_to(PROJECT_ROOT).parts
        )
    }
    return tuple(sorted(suites))


def find_requested_suites(kinds: Sequence[str]) -> tuple[Path, ...]:
    """Return the unique test directories for all requested categories."""
    suites = {suite for kind in kinds for suite in find_suites(kind)}
    return tuple(sorted(suites))


def run_kinds(kinds: Sequence[str], pytest_args: Sequence[str] = ()) -> bool:
    """Run requested colocated suites together in one pytest process."""
    if pytest_args:
        targets = tuple(pytest_args)
        print("Running selected pytest targets", flush=True)
    else:
        suites = find_requested_suites(kinds)
        if not suites:
            requested = ", ".join(kinds)
            print(f"ERROR: no {requested} test suites found", file=sys.stderr)
            return False
        targets = tuple(str(suite.relative_to(PROJECT_ROOT)) for suite in suites)
        labels = " + ".join(kinds)
        print(
            f"Running {len(targets)} {labels} test suite(s) in one pytest session",
            flush=True,
        )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *targets,
        ],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode == 0 or (
        not pytest_args and result.returncode == PYTEST_NO_TESTS_COLLECTED
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "suite",
        choices=("unit", "integration", "all"),
        help="Automated test category to run",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Optional pytest targets and flags; omit to run every suite in the category",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    kinds = tuple(SUITE_DIRECTORIES) if args.suite == "all" else (args.suite,)
    selected = args.pytest_args
    if selected[:1] == ["--"]:
        selected = selected[1:]
    return 0 if run_kinds(kinds, selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
