#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Enforce the weather frontend/domain boundary, not just interface documentation."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = (
    "controllers.weather",
    "protocols",
    "requests",
    "threading",
    "concurrent.futures",
    "apps.orcUi.composition",
    "frontends.common.map_weather_overlay_ui",
)
BACKEND_ATTRIBUTES = {
    "_provider",
    "_renderer",
    "_tiles",
    "_weather",
    "_cities",
    "_radar_controller",
    "_map_renderer",
}


def check_frontend(path, source):
    """Find provider/transport imports and backend-object inspection in a weather view."""
    errors = []
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        modules = (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module or ""]
            if isinstance(node, ast.ImportFrom)
            else []
        )
        for module in modules:
            if any(module == name or module.startswith(name + ".") for name in FORBIDDEN_IMPORTS):
                errors.append(f"{path}:{node.lineno}: weather view imports backend {module}")
        if isinstance(node, ast.Attribute) and node.attr in BACKEND_ATTRIBUTES:
            errors.append(
                f"{path}:{node.lineno}: weather view accesses backend attribute {node.attr}"
            )
    return errors


def check(root=ROOT):
    """Return the weather-specific rules used by the project-wide UI gate."""
    frontend = root / "apps/orcUi/frontend/tk"
    paths = (
        set(frontend.glob("*weather*.py"))
        | set(frontend.glob("*radar*.py"))
        | {frontend / "navigation_screen.py"}
    )
    paths |= set((root / "frontends/tk/weather").glob("*.py"))
    paths = {path for path in paths if path.is_file()}
    errors = []
    for path in sorted(paths):
        errors.extend(check_frontend(path.relative_to(root), path.read_text()))
    # Domain orchestration must remain independent of all GUI frameworks.
    for path in sorted((root / "controllers/weather").glob("*overlay_controller.py")) + [
        root / "controllers/weather/radar_replay_controller.py",
        root / "controllers/weather/weather_screen_controller.py",
    ]:
        if not path.is_file():
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            modules = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for module in modules:
                if module.split(".")[0] in {"tkinter", "PySide6", "PyQt6", "frontends", "apps"}:
                    errors.append(
                        f"{path.relative_to(root)}:{node.lineno}: weather controller imports frontend {module}"
                    )
    return paths, errors


def main():
    paths, errors = check()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Validated weather UI boundaries across {len(paths)} frontend modules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
