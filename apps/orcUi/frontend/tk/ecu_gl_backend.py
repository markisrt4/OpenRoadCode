# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Select the Tk OpenGL backend, including Python 3.14 on Termux:X11."""

import importlib
import importlib.util
import os
import sys


def load_gl_backend():
    """Return the frame and GL APIs without pyopengltk's Android import cycle."""
    if sys.platform == 'android':
        # Termux uses X11/GLX here, not an Android EGL window.
        os.environ.setdefault('PYOPENGL_PLATFORM', 'glx')
        if 'pyopengltk' not in sys.modules:
            spec = importlib.util.find_spec('pyopengltk')
            if spec is None:
                raise ModuleNotFoundError("No module named 'pyopengltk'")
            # Establish the installed package's namespace without executing its
            # linux/win32-only __init__. Its base and linux modules can then load
            # normally; exporting the frame also permits later opengl imports.
            package = importlib.util.module_from_spec(spec)
            sys.modules['pyopengltk'] = package
            try:
                package.OpenGLFrame = importlib.import_module('pyopengltk.linux').OpenGLFrame
            except Exception:
                for name in list(sys.modules):
                    if name == 'pyopengltk' or name.startswith('pyopengltk.'):
                        del sys.modules[name]
                raise
        from pyopengltk.linux import OpenGLFrame
    else:
        from pyopengltk import OpenGLFrame
    from OpenGL import GL, GLU
    return OpenGLFrame, GL, GLU
