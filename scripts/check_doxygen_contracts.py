#!/usr/bin/env python3
"""Validate Doxygen contracts on public interface methods."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "venv", "__pycache__"}
PARAM_PATTERN = r"(?m)^\s*[@\\]param(?:\s+\[[^]]+\])?\s+{name}\b"
RETURN_PATTERN = re.compile(r"(?m)^\s*[@\\](?:return|returns|retval)\b")


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return public parameter names excluding the instance/class receiver."""
    parameters = [
        argument.arg
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
        if argument.arg not in {"self", "cls"}
    ]
    if node.args.vararg is not None:
        parameters.append(node.args.vararg.arg)
    if node.args.kwarg is not None:
        parameters.append(node.args.kwarg.arg)
    return parameters


def _returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether the callable annotation declares a non-None result."""
    annotation = node.returns
    return annotation is not None and not (
        isinstance(annotation, ast.Constant) and annotation.value is None
    )


def main() -> int:
    """Check every public method declared by an explicit interface module."""
    failures: list[str] = []
    checked_methods = 0

    for path in sorted(PROJECT_ROOT.rglob("*_if.py")):
        if EXCLUDED_PARTS.intersection(path.parts):
            continue

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for class_node in tree.body:
            if not isinstance(class_node, ast.ClassDef):
                continue
            if class_node.name.startswith("_"):
                continue

            for method in class_node.body:
                if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if method.name.startswith("_"):
                    continue

                checked_methods += 1
                location = (
                    f"{path.relative_to(PROJECT_ROOT)}:"
                    f"{method.lineno}: {class_node.name}.{method.name}"
                )
                docstring = ast.get_docstring(method) or ""
                if not docstring:
                    failures.append(f"{location}: missing docstring")
                    continue

                for parameter in _parameters(method):
                    pattern = re.compile(
                        PARAM_PATTERN.format(name=re.escape(parameter))
                    )
                    if not pattern.search(docstring):
                        failures.append(
                            f"{location}: missing @param {parameter}"
                        )

                if _returns_value(method) and not RETURN_PATTERN.search(docstring):
                    failures.append(
                        f"{location}: missing @return or @retval"
                    )

    if failures:
        print("\n".join(failures), file=sys.stderr)
        print(
            f"{len(failures)} contract documentation error(s)",
            file=sys.stderr,
        )
        return 1

    print(
        f"Validated Doxygen contracts for {checked_methods} public "
        "interface methods."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
