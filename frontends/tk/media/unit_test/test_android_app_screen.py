# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Real Tk geometry/lifecycle checks; run with DISPLAY set to an X11 test server."""
import os
from dataclasses import replace
from unittest.mock import Mock
import tkinter as tk

import pytest

from frontends.tk.media.android_app_screen import AndroidAppScreen
from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from ui.navigation.android_app_view_if import AndroidAppViewState
from apps.orcUi.theme_runtime import theme_bundle
from ui.theme import ThemeMode


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='real Tk geometry needs X11')
def test_waze_hide_return_and_close_have_separate_lifetimes():
    root = tk.Tk()
    root.geometry('1200x700')
    parent = tk.Frame(root)
    parent.pack(fill='both', expand=True)
    host = Mock(screen_parent=parent)
    host.clear_screen_content.side_effect = lambda: [child.destroy() for child in parent.winfo_children()]
    player, close, requests = Mock(), Mock(), Mock()
    screen = AndroidAppScreen('waze', host, title='Waze', player=player,
        default_target='android', window_class='Weston Compositor', back_action=Mock(),
        preserve_external_window=True, keep_player_on_hide=True, close_action=close,
        map_runtime=Mock(), map_platform=Mock(), requests=requests, breadcrumb=Mock(),
        theme_bundle=lambda: theme_bundle(ThemeMode.DARK))
    screen._embedder = Mock(window_id=None)
    try:
        screen.present(AndroidAppViewState('Waze', 'com.waze', expanded=True, can_split=False,
                                           can_navigate_saved_destinations=True))
        screen.show()
        root.update()
        screen._launch_and_embed()
        screen.hide()
        player.stop.assert_not_called()
        screen.show()
        root.update()
        screen._launch_and_embed()
        player.stop.assert_not_called()
        assert screen._close_button.winfo_ismapped()
        assert screen._close_button.cget('text') == 'CLOSE WAZE'
        assert [button.cget('text') for button in screen._destination_buttons] == ['⌂ HOME', '▣ WORK']
        for button in screen._destination_buttons:
            assert button.winfo_ismapped()
            button.invoke()
        assert [call.args[0] for call in requests.request_navigate_saved_destination.call_args_list] == ['home', 'work']
        screen._close_button.invoke()
        close.assert_called_once_with()
        screen.close_session()
        player.stop.assert_called_once_with()
    finally:
        root.destroy()


@pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='real Tk geometry needs X11')
def test_waze_browser_fallback_back_button_survives_theme_change():
    root = tk.Tk()
    root.geometry('1200x700')
    host = Mock(screen_parent=root)
    back, player = Mock(), Mock()
    mode = [ThemeMode.DARK]
    screen = BrowserMediaScreen('waze', host, title='Waze Live Map', player=player,
        default_target='https://www.waze.com/live-map', window_class='waze',
        back_action=back, back_label='‹ BACK TO MAP', theme_request_handler=player,
        theme_bundle=lambda: theme_bundle(mode[0]), window_embedder=Mock(window_id=None))
    try:
        screen.show()
        root.update()
        button = screen._navigation.winfo_children()[0]
        assert button.winfo_ismapped()
        assert screen._navigation.winfo_height() > 20
        assert screen._browser_host.winfo_y() >= screen._navigation.winfo_height()
        button.invoke()
        back.assert_called_once_with()
        mode[0] = ThemeMode.LIGHT
        screen.set_theme_mode(mode[0])
        root.update()
        button = screen._navigation.winfo_children()[0]
        assert button.winfo_ismapped()
        assert button.cget('bg') == theme_bundle(mode[0]).ui.control_background
        button.invoke()
        assert back.call_count == 2
    finally:
        screen.hide()
        root.destroy()


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
        requests.request_set_android_app_visible.assert_called_with(True)
        screen.hide()
        requests.request_set_android_app_visible.assert_called_with(False)
    finally:
        screen.hide()
        root.destroy()
