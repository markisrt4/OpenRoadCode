# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Check the ECU graphics using the launcher's actual Python and display."""

import ctypes.util
import os
from pathlib import Path
import sys
import tkinter as tk

from ui.theme import load_theme_bundle
from .ecu_engine_gl import create_engine_gl


def main() -> int:
    print(f"Python: {sys.executable}", flush=True)
    print(f"Display: {os.environ.get('DISPLAY', '(unset)')}", flush=True)
    print(f"Renderer setting: {os.environ.get('OPENROAD_ECU_RENDERER', 'auto')}", flush=True)
    for library in ('GL', 'GLU', 'X11'):
        print(f"{library} library: {ctypes.util.find_library(library) or 'MISSING'}", flush=True)
    try:
        from OpenGL import GL
        import pyopengltk  # noqa: F401
    except (ImportError, OSError, RuntimeError) as exc:
        print(f"OpenGL import failed: {exc}", flush=True)
        print(f'Install into this interpreter: {sys.executable} -m pip install '
              'PyOpenGL==3.1.10 pyopengltk==0.0.4', flush=True)
        return 1
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"Display connection failed: {exc}", flush=True)
        return 1
    root.geometry('360x480')
    root.title('ECU OpenGL diagnostic')
    errors = []
    root.report_callback_exception = lambda kind, error, tb: errors.append(str(error))
    project = Path(__file__).resolve().parents[4]
    renderer = create_engine_gl(
        root, theme=load_theme_bundle(project/'resources/themes/orc-dark.css'),
        on_failure=lambda: None, on_unavailable=errors.append,
    )
    if renderer is not None:
        renderer.pack(fill='both', expand=True)
    result = 1

    def finish():
        nonlocal result
        if renderer is not None and renderer.context_created and not renderer.failed and not errors:
            renderer.tkMakeCurrent()
            print(f"OpenGL version: {GL.glGetString(GL.GL_VERSION)}", flush=True)
            print(f"OpenGL renderer: {GL.glGetString(GL.GL_RENDERER)}", flush=True)
            print('ECU OpenGL: OK', flush=True)
            result = 0
        else:
            print(f"ECU OpenGL: FAILED: {'; '.join(errors) or 'No GL context'}", flush=True)
        root.destroy()

    root.after(1500, finish)
    root.mainloop()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
