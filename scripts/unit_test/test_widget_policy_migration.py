# SPDX-License-Identifier: MIT

"""Active Tk presentation classes retain policy coverage and valid inheritance."""

import ast
import importlib
from pathlib import Path

import pytest

from ui import UiWidget


ROOT = Path(__file__).resolve().parents[2]
SCOPES = ('frontends/tk', 'apps/orcUi/frontend/tk', 'apps/common/instruments')
# These compose toolkit widgets rather than inheriting a toolkit class.
COMPOSITE_WIDGETS = {
    'BrowserReturnOverlay', 'SpotifyVideoOverlay', 'MenuRenderer', 'StartupSplash',
    'TkTooltip', 'NavigationRouteWeather', 'PowerDialog', 'OrcUiShellView', 'OrcUiApp',
}


def presentation_classes():
    for scope in SCOPES:
        for path in sorted((ROOT / scope).rglob('*.py')):
            if 'unit_test' in path.parts or '__pycache__' in path.parts:
                continue
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                bases = [ast.unparse(base) for base in node.bases]
                if (any(base.startswith(('tk.', 'ttk.')) for base in bases)
                        or node.name in COMPOSITE_WIDGETS):
                    module = '.'.join(path.relative_to(ROOT).with_suffix('').parts)
                    yield module, node.name


@pytest.mark.parametrize('module,name', list(presentation_classes()),
                         ids=lambda value: value)
def test_active_widget_imports_with_valid_mro_and_inherits_policy(module, name):
    # Importing the actual class also catches multiple-inheritance/metaclass
    # conflicts that an AST-only check cannot find. No Tk root is constructed.
    widget = getattr(importlib.import_module(module), name)
    assert issubclass(widget, UiWidget), f'{module}.{name} must inherit UiWidget'
    assert widget.__mro__.count(UiWidget) == 1
