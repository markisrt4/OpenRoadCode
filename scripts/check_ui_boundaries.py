#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Discover UI/domain modules and reject new architectural dependency violations."""
import ast
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'scripts/ui_boundary_exceptions.json'
UI_BACKENDS = ('controllers', 'services', 'protocols', 'hardware_io', 'requests',
               'httpx', 'urllib.request', 'threading', 'concurrent.futures', 'subprocess',
               'apps.orcUi.composition')
GUI = ('frontends', 'apps', 'tkinter', 'PySide6', 'PyQt6', 'PyQt5')


def production(path):
    """Exclude test suites and generated Python files."""
    return not any(part in {'unit_test', 'integration_test', 'component_test', '__pycache__'}
                   for part in path.parts) and not path.name.startswith('test_')


def discover(root):
    """Automatically include new frontend, screen, domain, and contract modules."""
    paths = set((root / 'frontends').rglob('*.py'))
    for directory in ('frontend', 'screens'):
        paths.update(path for path in (root / 'apps').rglob('*.py') if directory in path.parts)
    paths.update((root / 'controllers').rglob('*.py'))
    paths.update((root / 'ui').rglob('*.py'))
    return sorted(path for path in paths if production(path.relative_to(root)))


def violations(path, source):
    """Return stable dependency identifiers plus diagnostic source locations."""
    parts = Path(path).parts
    contract = parts[0] == 'ui'
    domain = parts[0] == 'controllers'
    forbidden = GUI if domain else UI_BACKENDS + GUI if contract else UI_BACKENDS
    results = []
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if node.level:
                relative = Path(*parts[:-1])
                for _ in range(node.level - 1):
                    relative = relative.parent
                module = '.'.join(relative.parts + tuple(module.split('.'))).rstrip('.')
            modules = [f'{module}.{alias.name}' for alias in node.names]
        else:
            continue
        for module in modules:
            if any(module == prefix or module.startswith(prefix + '.') for prefix in forbidden):
                results.append((f'{path}|imports {module}', node.lineno))
    return results


def check(root, baseline):
    """Reject new violations, expanded exceptions, and stale baseline entries."""
    actual = Counter()
    locations = {}
    paths = discover(root)
    for path in paths:
        for key, line in violations(path.relative_to(root).as_posix(), path.read_text()):
            actual[key] += 1
            locations[key] = line
    errors = []
    for key, count in actual.items():
        allowed = baseline.get(key, {}).get('count', 0)
        if count > allowed:
            errors.append(f'{key} (line {locations[key]}): {count - allowed} new violation(s)')
    for key, entry in baseline.items():
        if not entry.get('reason') or not isinstance(entry.get('count'), int) or entry['count'] < 1:
            errors.append(f'{key}: invalid exception; positive count and reason required')
        elif actual[key] < entry['count']:
            errors.append(f'{key}: remove or reduce stale exception ({actual[key]} remaining)')
    return paths, errors


def main():
    baseline = json.loads(BASELINE.read_text())
    paths, errors = check(ROOT, baseline)
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Validated UI boundaries across {len(paths)} modules; '
          f'{sum(entry["count"] for entry in baseline.values())} explicit legacy dependency exceptions.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
