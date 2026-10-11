# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Exercise native GL scenes and cleanup on a real X11 display, without audio."""
import tkinter as tk
from types import SimpleNamespace

import numpy as np

from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
from frontends.tk.media.native_music_visualizer import NativeMusicVisualizerPanel
from ui.music_visualizer import VisualizerFrame


def main():
    root = tk.Tk()
    root.geometry('900x650')
    root.title('ORC native music visualizer component check')
    errors = []
    root.report_callback_exception = lambda *args: errors.append(args)
    panel = NativeMusicVisualizerPanel(
        root, theme_bundle=SimpleNamespace(ui=SimpleNamespace(background='#07121c')),
        gl_backend=load_gl_backend,
    )
    panel.pack(fill='both', expand=True)

    def check():
        try:
            from OpenGL import GL
            assert panel._surface is not None and panel._surface.context_created, panel._message.get()
            captures = []
            for view, double in [('tunnel', False), ('drums', False), ('drums', True)]:
                panel._select_view(view)
                panel._double.set(double)
                panel.set_analysis_frame(VisualizerFrame(.7, .6, .4, .2, (.4,)*24,
                                                       beat=1, kick=1, snare=.8, cymbal=.7))
                panel._surface.tkMakeCurrent()
                panel._draw(GL, panel._glu, panel._surface)
                GL.glFinish()
                GL.glReadBuffer(GL.GL_BACK)
                width, height = panel._surface.winfo_width(), panel._surface.winfo_height()
                pixels = np.frombuffer(GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE), dtype=np.uint8)
                assert np.std(pixels) > 5, f'{view} produced an empty image'
                assert GL.glGetError() == GL.GL_NO_ERROR
                captures.append(pixels.copy())
            assert not np.array_equal(captures[1], captures[2]), 'Double kick did not change the scene'
            assert not errors, errors
            print('PASS: native tunnel, 3D drum kit, double kick, nonempty frames, GL errors, cleanup')
            print('Renderer:', GL.glGetString(GL.GL_RENDERER).decode())
        except Exception as exc:
            errors.append(exc)
        finally:
            panel.close()
            assert panel._job is None
            panel.destroy()
            root.destroy()

    root.after(1000, check)
    root.mainloop()
    if errors:
        raise RuntimeError(errors)


if __name__ == '__main__':
    main()
