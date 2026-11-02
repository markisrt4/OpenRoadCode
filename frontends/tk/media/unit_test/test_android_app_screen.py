# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Real Tk geometry/lifecycle checks; run with DISPLAY set to an X11 test server."""
import os
from dataclasses import replace
from unittest.mock import Mock
import tkinter as tk

import pytest

from frontends.tk.media.android_app_screen import AndroidAppScreen
from ui.navigation.android_app_view_if import AndroidAppViewState
from apps.orcUi.theme_runtime import theme_bundle
from ui.theme import ThemeMode


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='real Tk geometry needs X11')
def test_equal_split_expand_restore_and_stale_mount():
    root = tk.Tk()
    root.geometry('1200x700')
    parent = tk.Frame(root)
    parent.pack(fill='both', expand=True)
    host = Mock(screen_parent=parent)
    callbacks = []
    host.schedule_ui_callback.side_effect = lambda delay, callback: callbacks.append(callback) or len(callbacks)
    runtime, platform, player, requests, breadcrumb = Mock(), Mock(), Mock(), Mock(), Mock()
    presentation = Mock()
    mode = [ThemeMode.DARK]
    screen = AndroidAppScreen('android', host, title='Android', player=player,
        default_target='android', window_class='Weston Compositor', back_action=Mock(),
        preserve_external_window=True, map_runtime=runtime, map_platform=platform,
        requests=requests, breadcrumb=breadcrumb, theme_bundle=lambda: theme_bundle(mode[0]),
        theme_request_handler=player, map_presentation=presentation)
    screen._embedder = Mock(window_id=None)
    try:
        state = AndroidAppViewState('Panera Bread', 'com.panera.bread')
        screen.present(state)
        screen.show()
        root.update()
        assert screen._expand_button.cget('text') == 'FULL SCREEN APP'
        # Allow the gutter and Tk's integer column rounding.
        assert abs(screen._map_host.winfo_width() - screen._browser_host.winfo_width()) <= 5
        assert screen._browser_host.winfo_width() > 500
        breadcrumb.assert_called_with('Panera Bread')
        host.set_screen_title.assert_called_with('Panera Bread')
        pending = callbacks[0]
        pending()
        screen._launch_and_embed()
        runtime.launch.assert_called_once()
        presentation.request_replay_map_presentation.assert_called_once()
        player.play.assert_called_once()
        screen._expand_button.invoke()
        requests.request_toggle_android_app_expanded.assert_called_once()
        screen.present(state)
        screen._embedder.set_vertical_crop.assert_called_with(32, 48)
        screen.present(replace(state, expanded=True))
        root.update()
        assert screen._browser_host.winfo_width() >= 1190
        assert screen._expand_button.cget('text') == 'SPLIT VIEW'
        screen._embedder.resize.assert_called_with(screen._browser_host.winfo_width(), screen._browser_host.winfo_height())
        assert screen._back_button.cget('relief') == 'flat'
        assert int(screen._back_button.cget('borderwidth')) == 0
        assert screen._back_button.cget('background') == theme_bundle(ThemeMode.DARK).ui.control_background
        assert screen._vertical_crop == (32, 48)
        assert not any(isinstance(widget, tk.Button) and 'Android frame' in widget.cget('text')
                       for widget in screen._toolbar.winfo_children())
        runtime.stop.assert_called_once()
        screen.present(state)
        root.update()
        assert screen._expand_button.cget('text') == 'FULL SCREEN APP'
        assert abs(screen._map_host.winfo_width() - screen._browser_host.winfo_width()) <= 5
        mode[0] = ThemeMode.LIGHT
        screen.set_theme_mode(ThemeMode.LIGHT)
        assert screen._back_button.cget('background') == theme_bundle(ThemeMode.LIGHT).ui.control_background
        assert screen._expand_button.cget('foreground') == theme_bundle(ThemeMode.LIGHT).ui.control_text
        stale = callbacks[-1]
        count = presentation.request_replay_map_presentation.call_count
        screen.hide()
        stale()
        assert presentation.request_replay_map_presentation.call_count == count
        assert runtime.launch.call_count == 1
        assert player.play.call_count == 1
        screen.present(AndroidAppViewState('Waze', 'com.waze', expanded=True, can_split=False))
        screen.show()
        root.update()
        assert screen._browser_host.winfo_width() >= 1190
        assert not screen._expand_button.winfo_ismapped()
        assert not screen._map_host.winfo_ismapped()
        assert screen._back_button.winfo_ismapped()
    finally:
        screen.hide()
        root.destroy()
