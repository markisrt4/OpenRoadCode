# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Protect visualizer dependencies across the application and frontend boundaries."""
import ast
from pathlib import Path


def test_reusable_visualizer_layers_do_not_import_application_or_capture_infrastructure():
    root = Path(__file__).resolve().parents[4]
    layers = {
        'ui/music_visualizer': ('apps', 'frontends', 'controllers', 'tkinter'),
        'frontends/tk/media': ('apps', 'controllers.audio.capture', 'controllers.audio.music_analysis'),
        'controllers/audio/music_analysis': ('apps', 'frontends', 'tkinter'),
    }
    for directory, forbidden in layers.items():
        for path in (root / directory).glob('*.py'):
            if directory == 'frontends/tk/media' and not path.name.startswith('music_visualizer'):
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                modules = ([node.module or ''] if isinstance(node, ast.ImportFrom)
                           else [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
                for module in modules:
                    assert not any(module == prefix or module.startswith(prefix + '.')
                                   for prefix in forbidden), f'{path}: forbidden dependency {module}'
