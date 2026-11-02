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
    screen = AndroidAppScreen('android', host, title='Android', player=player,
        default_target='android', window_class='Weston Compositor', back_action=Mock(),
        preserve_external_window=True, map_runtime=runtime, map_platform=platform,
        requests=requests, breadcrumb=breadcrumb)
    screen._embedder = Mock(window_id=None)
    try:
        state = AndroidAppViewState('Panera Bread', 'com.panera.bread')
        screen.present(state)
        screen.show()
        root.update()
        # Allow the gutter and Tk's integer column rounding.
        assert abs(screen._map_host.winfo_width() - screen._browser_host.winfo_width()) <= 5
        assert screen._browser_host.winfo_width() > 500
        breadcrumb.assert_called_with('Panera Bread')
        host.set_screen_title.assert_called_with('Panera Bread')
        pending = callbacks[0]
        pending()
        screen._launch_and_embed()
        runtime.launch.assert_called_once()
        player.play.assert_called_once()
        screen._expand_button.invoke()
        requests.request_toggle_android_app_expanded.assert_called_once()
        screen._trim_button.invoke()
        requests.request_toggle_android_frame_trim.assert_called_once()
        screen.present(replace(state, trim_android_frame=True))
        screen._embedder.set_vertical_crop.assert_called_with(56, 48)
        screen.present(replace(state, expanded=True))
        root.update()
        assert screen._browser_host.winfo_width() >= 1190
        runtime.stop.assert_called_once()
        screen.present(state)
        root.update()
        assert abs(screen._map_host.winfo_width() - screen._browser_host.winfo_width()) <= 5
        stale = callbacks[-1]
        screen.hide()
        stale()
        assert runtime.launch.call_count == 1
        assert player.play.call_count == 1
    finally:
        screen.hide()
        root.destroy()
