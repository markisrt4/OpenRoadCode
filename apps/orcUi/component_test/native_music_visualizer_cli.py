# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Exercise the native ORC layout and every GL scene on X11, without microphone."""
from dataclasses import replace
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
from frontends.tk.media.native_music_visualizer import NativeMusicVisualizerPanel
from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from frontends.tk.media.music_gl_scene import MODE_LABELS
from ui.music_visualizer import KickMode, MusicVisualizerSource, VisualizerFrame
from ui.music_visualizer.music_visualizer_types import MusicVisualizerView
from ui.theme import ThemeMode
from apps.orcUi.theme_runtime import theme_bundle


def main():
    root = tk.Tk()
    root.geometry('900x650')
    root.title('ORC native music visualizer component check')
    errors = []
    root.report_callback_exception = lambda *args: errors.append(args)
    parent = tk.Frame(root)
    parent.pack(fill='both', expand=True)
    host = SimpleNamespace(
        screen_parent=parent, activate_screen=lambda _: None,
        clear_screen_content=lambda: [w.destroy() for w in parent.winfo_children()],
        set_screen_title=lambda _: None, schedule_ui_callback=root.after,
        cancel_ui_callback=root.after_cancel,
    )
    controller = Mock()
    controller.presentation.return_value = (None, None)
    screen = MusicVisualizerScreen(
        host, on_back=lambda: None, controller=controller,
        theme_bundle=lambda: theme_bundle(ThemeMode.DARK),
        initial_source=MusicVisualizerSource.ANDROID_PLAYBACK, native_controls=True,
        panel_factory=lambda parent, **kw: NativeMusicVisualizerPanel(parent, gl_backend=load_gl_backend, **kw),
    )
    screen.show()

    def check():
        try:
            from OpenGL import GL
            panel = screen._panel
            assert panel._surface is not None and panel._surface.context_created, panel.presentation_status()
            assert screen._render_parent.winfo_x() >= 164
            assert screen._controls.winfo_rootx() < screen._render_parent.winfo_rootx()
            assert panel._surface.winfo_height() >= parent.winfo_height() - 4
            captures = []
            configurations = [(mode, MusicVisualizerView.VISUALIZER, KickMode.SINGLE, True)
                              for mode in MODE_LABELS]
            configurations += [(screen._options.mode, MusicVisualizerView.DRUM_KIT, KickMode.SINGLE, True),
                               (screen._options.mode, MusicVisualizerView.DRUM_KIT, KickMode.DOUBLE, True),
                               (screen._options.mode, MusicVisualizerView.DRUM_KIT, KickMode.DOUBLE, False)]
            for mode, view, kick_mode, sticks in configurations:
                if view is MusicVisualizerView.VISUALIZER:
                    screen._mode_picker['menu'].invoke(list(MODE_LABELS).index(mode))
                    assert screen._options.mode is mode
                    assert screen._mode_name.get() == MODE_LABELS[mode]
                screen._set_options(mode=mode, view=view, kick_mode=kick_mode, show_sticks=sticks)
                panel.set_analysis_frame(VisualizerFrame(.7, .6, .4, .2, (.4,)*24,
                                                       beat=1, kick=1, snare=.8, cymbal=.7))
                panel._surface.tkMakeCurrent()
                panel._draw(GL, panel._glu, panel._surface)
                GL.glFinish()
                GL.glReadBuffer(GL.GL_BACK)
                width, height = panel._surface.winfo_width(), panel._surface.winfo_height()
                pixels = np.frombuffer(GL.glReadPixels(0, 0, width, height, GL.GL_RGB, GL.GL_UNSIGNED_BYTE), dtype=np.uint8)
                assert np.std(pixels) > 5, f'{mode.value}/{view.value} produced an empty image'
                assert GL.glGetError() == GL.GL_NO_ERROR
                captures.append(pixels.copy())
            for i, pixels in enumerate(captures):
                assert not any(np.array_equal(pixels, prior) for prior in captures[:i]), f'Scene {i} did not change'
            controller.start.assert_not_called()
            assert not errors, errors
            # Resize and zoom must preserve a valid GL context on small ORC windows.
            root.geometry('580x360')
            root.update_idletasks()
            panel.configure_visualizer(replace(screen._options, drum_zoom=2.8))
            panel._surface._display()
            assert GL.glGetError() == GL.GL_NO_ERROR
            print('PASS: themed left controls, nine distinct native scenes, drum zoom, sticks, double kick, resize, cleanup')
            print('Renderer:', GL.glGetString(GL.GL_RENDERER).decode())
        except Exception as exc:
            errors.append(exc)
        finally:
            screen.hide()
            assert panel._job is None
            screen.close()
            root.destroy()

    root.after(1000, check)
    root.mainloop()
    if errors:
        raise RuntimeError(errors)


if __name__ == '__main__':
    main()
