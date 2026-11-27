# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Exercise Android import routing without requiring native GPU libraries."""

import os
import subprocess
import sys
from pathlib import Path


def test_android_loads_x11_backend_without_changing_platform(tmp_path):
    package = tmp_path / "pyopengltk"
    package.mkdir()
    (package / "__init__.py").write_text("raise AssertionError('Android initializer executed')")
    (package / "linux.py").write_text("from OpenGL import GL, GLU\nclass OpenGLFrame: pass\n")
    (package / "opengl.py").write_text("from . import OpenGLFrame\n")
    gl = tmp_path / "OpenGL"
    gl.mkdir()
    (gl / "__init__.py").write_text("")
    (gl / "GL.py").write_text("")
    (gl / "GLU.py").write_text("")
    root = Path(__file__).resolve().parents[5]
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join((str(tmp_path), str(root))))
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import sys
sys.platform = 'android'
from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
frame, gl, glu = load_gl_backend()
assert frame.__module__ == 'pyopengltk.linux'
assert sys.platform == 'android'
assert gl.__name__ == 'OpenGL.GL'
assert glu.__name__ == 'OpenGL.GLU'
import pyopengltk.opengl
assert load_gl_backend()[0] is frame
""",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
