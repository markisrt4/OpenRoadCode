# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Exercise Android backend imports in a fresh interpreter."""

import importlib.util
import subprocess
import sys

import pytest


def test_android_loads_x11_backend_without_changing_platform():
    if importlib.util.find_spec('pyopengltk') is None:
        pytest.skip('Optional OpenGL backend not installed')
    result = subprocess.run(
        [sys.executable, '-c', '''
import sys
sys.platform = 'android'
from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
frame, gl, glu = load_gl_backend()
assert frame.__module__ == 'pyopengltk.linux'
assert sys.platform == 'android'
import pyopengltk.opengl
assert load_gl_backend()[0] is frame
'''], capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
