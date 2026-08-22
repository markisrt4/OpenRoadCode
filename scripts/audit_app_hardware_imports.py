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
    for path in sorted(APPS.rglob("*.py")):
        relative = path.relative_to(ROOT)
        for line, statement in hardware_imports(path):
            count += 1
            print(f"{relative}:{line}: {statement}")
    print(f"\n{count} direct hardware_io import(s) under apps/")
    print("Review each result: composition/diagnostics may be valid; telemetry consumers are suspect.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
