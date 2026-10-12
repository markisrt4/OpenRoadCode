# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Exercise the native ORC layout and every GL scene on X11, without microphone."""
from dataclasses import replace
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
from frontends.tk.media.native_music_visualizer import NativeMusicVisualizerPanel
from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from frontends.tk.media.music_gl_scene import MODE_LABELS
from ui.music_visualizer import KickMode, MusicVisualizerSource, VisualizerFrame
from ui.music_visualizer.music_visualizer_types import AnalyzerAppearance, AnalyzerPalette, MusicVisualizerView
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
            assert screen._render_parent.winfo_x() >= 180
            assert screen._controls.winfo_rootx() < screen._render_parent.winfo_rootx()
            assert panel._surface.winfo_height() >= parent.winfo_height() - 4
            captures = []
            configurations = [(mode, MusicVisualizerView.VISUALIZER, KickMode.SINGLE)
                              for mode in MODE_LABELS]
            configurations += [(screen._options.mode, MusicVisualizerView.DRUM_KIT, KickMode.SINGLE),
                               (screen._options.mode, MusicVisualizerView.DRUM_KIT, KickMode.DOUBLE)]
            for mode, view, kick_mode in configurations:
                if view is MusicVisualizerView.VISUALIZER:
                    screen._mode_buttons[mode].invoke()
                    assert screen._mode_buttons[mode].cget('bg') == screen._ui.accent_primary
                    assert sum(button.cget('bg') == screen._ui.accent_primary
                               for button in screen._mode_buttons.values()) == 1
                    assert screen._options.mode is mode
                    assert screen._mode_name.get() == MODE_LABELS[mode]
                screen._set_options(mode=mode, view=view, kick_mode=kick_mode)
                panel.set_analysis_frame(VisualizerFrame(.7, .6, .4, .2, (.4,)*24,
                                                       beat=1, kick=1, snare=.8, cymbal=.7,
                                                       spectrum_hz=tuple(float(i * 24) for i in range(700)),
                                                       spectrum_dbfs=tuple(-12.0 - i % 30 for i in range(700))))
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
            root.geometry('580x250')
            root.update_idletasks()
            panel.configure_visualizer(replace(screen._options, drum_zoom=2.8))
            panel._surface._display()
            assert GL.glGetError() == GL.GL_NO_ERROR
            # All control pages fit without a scrollbar even on a short viewport.
            for view in [MusicVisualizerView.VISUALIZER, MusicVisualizerView.DRUM_KIT]:
                screen._select_view(view)
                for page in ['AUDIO', 'SCENE', 'STYLE']:
                    screen._show_page(page)
                    root.update_idletasks()
                    assert screen._controls.winfo_reqheight() <= parent.winfo_height(), (view, page, screen._controls.winfo_reqheight())
                    def assert_controls_fit(widget):
                        if widget.winfo_ismapped():
                            assert widget.winfo_height() >= widget.winfo_reqheight(), (widget.winfo_class(), widget.winfo_height(), widget.winfo_reqheight())
                            for child in widget.winfo_children():
                                assert_controls_fit(child)
                    assert_controls_fit(screen._controls)
                    if page == 'STYLE':
                        for tab in ('LOOK', 'COLOR', 'MOTION', 'LABELS'):
                            screen._style_page._buttons[tab].invoke()
                            root.update_idletasks()
                            assert screen._controls.winfo_reqheight() <= parent.winfo_height(), (tab, screen._controls.winfo_reqheight())
                            assert_controls_fit(screen._controls)
                            for button in screen._style_page._buttons.values():
                                assert button.winfo_ismapped()
                                assert button.winfo_width() >= button.winfo_reqwidth()
                                assert button.winfo_x() + button.winfo_width() <= button.master.winfo_width()
                        appearance_controls = screen._style_page
                        before = screen._options.analyzer
                        with patch('frontends.tk.media.analyzer_appearance_controls.colorchooser.askcolor',
                                   return_value=(None, None)):
                            appearance_controls._choose_color('low_color')
                        assert screen._options.analyzer == before
                        with patch('frontends.tk.media.analyzer_appearance_controls.colorchooser.askcolor',
                                   return_value=((255, 128, 0), '#ff8000')):
                            appearance_controls._choose_color('low_color')
                        assert screen._options.analyzer.palette is AnalyzerPalette.CUSTOM
                        assert screen._options.analyzer.low_color == (1, 128/255, 0)
                        assert panel._render_settings.analyzer == screen._options.analyzer
                        appearance_controls._show('LOOK')
                        toggles = [child for child in appearance_controls._body.winfo_children()
                                   if isinstance(child, tk.Checkbutton)]
                        toggles[0].invoke()
                        assert screen._options.analyzer.segmented
                        toggles[1].invoke()
                        assert not screen._options.analyzer.peak_markers
                        appearance_controls._show('LABELS')
                        for child in appearance_controls._body.winfo_children():
                            if isinstance(child, tk.Checkbutton):
                                child.invoke()
                        assert not screen._options.analyzer.frequency_labels
                        assert not screen._options.analyzer.range_guides
                        panel._surface._display()
                        assert GL.glGetError() == GL.GL_NO_ERROR
                        appearance_controls._reset()
                        assert screen._options.analyzer == AnalyzerAppearance()
                        controller.start.assert_not_called()
                    if view is MusicVisualizerView.DRUM_KIT and page == 'SCENE':
                        buttons = [child for row in screen._scene_page.winfo_children()
                                   for child in row.winfo_children()
                                   if isinstance(child, tk.Button) and child.cget('text') in ('+', '−')]
                        assert len(buttons) == 4
                        plus = next(button for button in buttons if button.cget('text') == '+')
                        minus = next(button for button in buttons if button.cget('text') == '−')
                        for _ in range(30):
                            plus.invoke()
                        assert screen._options.drum_gain == 1.2
                        for _ in range(30):
                            minus.invoke()
                        assert screen._options.drum_gain == .2
                        controller.start.assert_not_called()
            print('PASS: compact controls, ten native scenes, detailed drums, softer response, double kick, custom appearance, 250px viewport, cleanup')
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
