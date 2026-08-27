#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Report direct hardware_io imports below apps/ for architecture review."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPS = ROOT / "apps"


def hardware_imports(path: Path) -> list[tuple[int, str]]:
    """Return direct hardware_io imports from one parseable Python source file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("hardware_io"):
            findings.append((node.lineno, f"from {node.module} import ..."))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("hardware_io"):
                    findings.append((node.lineno, f"import {alias.name}"))
    return sorted(findings)


def main() -> int:
    count = 0
    skipped: list[tuple[Path, SyntaxError]] = []
    for path in sorted(APPS.rglob("*.py")):
        relative = path.relative_to(ROOT)
        try:
            findings = hardware_imports(path)
        except SyntaxError as error:
            skipped.append((relative, error))
            continue
        for line, statement in findings:
            count += 1
            print(f"{relative}:{line}: {statement}")

    print(f"\n{count} direct hardware_io import(s) under apps/")
    print("Review each result: composition/diagnostics may be valid; telemetry consumers are suspect.")

    if skipped:
        print(f"\nSkipped {len(skipped)} source file(s) that could not be parsed:")
        for path, error in skipped:
            location = f":{error.lineno}" if error.lineno is not None else ""
            print(f"  {path}{location}: {error.msg}")
        print("These files are reported separately so legacy/deprecated syntax cannot hide other findings.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
