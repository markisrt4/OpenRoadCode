# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Verify HOME/full native view handoff with one shared synthetic PCM session."""
from functools import partial
import tkinter as tk
from types import SimpleNamespace

import numpy as np

from apps.orcUi.frontend.tk.ecu_gl_backend import load_gl_backend
from apps.orcUi.theme_runtime import theme_bundle
from controllers.audio.music_analysis.music_analysis_session import PushAudioCapture
from controllers.audio.music_analysis.music_visualizer_controller import MusicVisualizerController
from controllers.audio.music_analysis.music_visualizer_session import MusicVisualizerSession
from frontends.tk.media.home_media_visualizer import HomeMediaVisualizer
from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from frontends.tk.media.native_music_visualizer import NativeMusicVisualizerPanel
from ui.music_visualizer import MusicVisualizerSource
from ui.music_visualizer.music_visualizer_types import MusicVisualizationMode
from ui.theme import ThemeMode


def main():
    root = tk.Tk()
    root.geometry('700x400')
    root.title('ORC HOME/shared audio component check')
    parent = tk.Frame(root)
    parent.pack(fill=tk.BOTH, expand=True)
    errors, captures = [], []
    root.report_callback_exception = lambda *exc: errors.append(exc)
    theme = lambda: theme_bundle(ThemeMode.DARK)
    def session_factory(callback, *, source):
        capture = PushAudioCapture()
        captures.append(capture)
        return MusicVisualizerSession(lambda: capture, callback)
    controller = MusicVisualizerController(session_factory)
    panel_factory = partial(NativeMusicVisualizerPanel, gl_backend=load_gl_backend)
    host = SimpleNamespace(
        screen_parent=parent, activate_screen=lambda _: None,
        clear_screen_content=lambda: [w.destroy() for w in parent.winfo_children()],
        set_screen_title=lambda _: None, schedule_ui_callback=root.after,
        cancel_ui_callback=root.after_cancel,
    )
    screen = MusicVisualizerScreen(host, on_back=lambda: None, theme_bundle=theme,
                                   controller=controller, panel_factory=panel_factory,
                                   initial_source=MusicVisualizerSource.ANDROID_PLAYBACK,
                                   native_controls=True, share_session=True)
    def create_card():
        card = HomeMediaVisualizer(
            parent, controller=controller, theme_bundle=theme,
            now_playing_factory=lambda owner: tk.Label(owner, text='Now playing'),
            visualizer_factory=lambda owner: panel_factory(owner, theme_bundle=theme()),
            source=MusicVisualizerSource.ANDROID_PLAYBACK, on_open=screen.show,
        )
        card.pack(fill=tk.BOTH, expand=True)
        return card
    card = create_card()
    card._select(True)
    controller.start(MusicVisualizerSource.ANDROID_PLAYBACK)
    rate = 48000
    tone = .5 * np.sin(np.arange(2048) * 2 * np.pi * 70 / rate)
    def feed():
        if captures and captures[0].is_running:
            captures[0].push(tone, rate)
        if root.winfo_exists():
            root.after(45, feed)
    root.after(50, feed)

    def inspect_home():
        try:
            assert len(captures) == 1 and controller.latest_frame().level > 0
            assert card._preview._surface.context_created
            screen.show()
            screen._select_visualizer('Frequency Analyzer')
            screen._style_page._change(segmented=True, spacing=.4, decay_s=.8)
            root.after(400, inspect_full)
        except Exception as exc:
            fail(exc)
    def inspect_full():
        try:
            assert len(captures) == 1 and captures[0].is_running
            assert screen._panel._surface.context_created
            assert controller.visualizer_options().mode is MusicVisualizationMode.BOOMBOX
            screen.hide()
            for widget in parent.winfo_children():
                widget.destroy()
            returned = create_card()
            assert returned._preview is not None
            assert controller.home_visualizer_enabled()
            root.after(400, lambda: inspect_returned(returned))
        except Exception as exc:
            fail(exc)
    def inspect_returned(returned):
        try:
            assert len(captures) == 1 and captures[0].is_running
            assert controller.visualizer_options().mode is MusicVisualizationMode.BOOMBOX
            assert returned._preview._surface.context_created
            assert returned._preview._render_settings.analyzer == controller.visualizer_options().analyzer
            assert returned._preview._render_settings.analyzer.segmented
            assert returned._preview._render_settings.analyzer.spacing == .4
            assert returned._preview._render_settings.analyzer.decay_s == .8
            returned._select(False)
            root.after(400, inspect_released)
        except Exception as exc:
            fail(exc)
    def inspect_released():
        try:
            assert not captures[0].is_running
            assert controller.latest_frame() is None
            assert not errors, errors
            print('PASS: HOME preview → full visualizer → HOME uses one PCM capture, preset and custom appearance; now-playing releases it')
        except Exception as exc:
            errors.append(exc)
        finally:
            finish()
    def finish():
        screen.close()
        for widget in parent.winfo_children():
            widget.destroy()
        controller.close()
        root.destroy()
    def fail(exc):
        errors.append(exc)
        finish()
    root.after(1000, inspect_home)
    root.mainloop()
    if errors:
        raise RuntimeError(errors)


if __name__ == '__main__':
    main()
