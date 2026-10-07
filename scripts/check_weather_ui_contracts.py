#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Enforce the weather frontend/domain boundary, not just interface documentation."""

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / 'apps/orcUi/frontend/tk'
FORBIDDEN_IMPORTS = ('controllers.weather', 'protocols', 'requests', 'threading', 'concurrent.futures',
                     'apps.orcUi.composition', 'frontends.common.map_weather_overlay_ui')
BACKEND_ATTRIBUTES = {'_provider', '_renderer', '_tiles', '_weather', '_cities', '_radar_controller', '_map_renderer'}


def check_frontend(path, source):
    """Find provider/transport imports and backend-object inspection in a weather view."""
    errors = []
    tree = ast.parse(source, filename=str(path))
    for node in ast.walk(tree):
        modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                   else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
        for module in modules:
            if any(module == name or module.startswith(name + '.') for name in FORBIDDEN_IMPORTS):
                errors.append(f'{path}:{node.lineno}: weather view imports backend {module}')
        if isinstance(node, ast.Attribute) and node.attr in BACKEND_ATTRIBUTES:
            errors.append(f'{path}:{node.lineno}: weather view accesses backend attribute {node.attr}')
    return errors


def main():
    paths = set(FRONTEND.glob('*weather*.py')) | set(FRONTEND.glob('*radar*.py')) | {FRONTEND / 'navigation_screen.py'}
    paths |= set((ROOT / 'frontends/tk/weather').glob('*.py'))
    errors = []
    for path in sorted(paths):
        errors.extend(check_frontend(path.relative_to(ROOT), path.read_text()))
    # Domain orchestration must remain independent of all GUI frameworks.
    for path in sorted((ROOT / 'controllers/weather').glob('*overlay_controller.py')) + [ROOT / 'controllers/weather/radar_replay_controller.py', ROOT / 'controllers/weather/weather_screen_controller.py']:
        for node in ast.walk(ast.parse(path.read_text())):
            modules = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                       else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            for module in modules:
                if module.split('.')[0] in {'tkinter', 'PySide6', 'PyQt6', 'frontends', 'apps'}:
                    errors.append(f'{path.relative_to(ROOT)}:{node.lineno}: weather controller imports frontend {module}')
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Validated weather UI boundaries across {len(paths)} frontend modules.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
