# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from unittest.mock import Mock, patch
import subprocess

import pytest

from apps.orcUi.composition.android_app_view import AndroidAppView
from apps.orcUi.adapters.waydroid_surface_player import WaydroidSurfacePlayer
from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from frontends.x11.x11_window_embedder import X11WindowEmbedder


def test_worker_request_dispatches_and_close_discards_queued_open():
    app = Mock()
    with patch('apps.orcUi.composition.android_app_view.AndroidAppScreen') as screen:
        view = AndroidAppView(app, map_runtime=Mock(), map_platform=Mock())
        view.request_show_android_app('Panera Bread', 'com.panera.bread')
        app.navigate_to.assert_not_called()
        first = app.dispatch_ui.call_args.args[0]
        first()
        assert screen.return_value.present.call_args.args[0].app_name == 'Panera Bread'
        app.navigate_to.assert_called_once_with('ANDROID_APP')
        view.request_show_android_app()
        queued = app.dispatch_ui.call_args.args[0]
        view.close()
        view.close()
        queued()
        view.request_show_android_app()
        assert app.navigate_to.call_count == 1
        assert app.dispatch_ui.call_count == 2
        screen.return_value.hide.assert_called_once()
        options = screen.call_args.kwargs
        assert options['preserve_external_window'] is True
        options['back_action']()
        app.navigate_to.assert_called_with('NAVIGATION')
        options['breadcrumb']('Panera Bread')
        app.set_breadcrumb.assert_called_once_with('NAV', 'Panera Bread')


def test_expand_collapses_with_no_app_relaunch_and_next_app_starts_split():
    app = Mock()
    with patch('apps.orcUi.composition.android_app_view.AndroidAppScreen') as screen:
        view = AndroidAppView(app, map_runtime=Mock(), map_platform=Mock())
        view.request_show_android_app('Panera Bread', 'com.panera.bread')
        app.dispatch_ui.call_args.args[0]()
        view.request_toggle_android_app_expanded()
        assert screen.return_value.present.call_args.args[0].expanded
        view.request_toggle_android_app_expanded()
        assert not screen.return_value.present.call_args.args[0].expanded
        assert app.navigate_to.call_count == 1
        view.request_toggle_android_app_expanded()
        view.request_show_android_app('Maps', 'com.google.android.apps.maps')
        app.dispatch_ui.call_args.args[0]()
        state = screen.return_value.present.call_args.args[0]
        assert state.app_name == 'Maps'
        assert not state.expanded
        view.request_toggle_android_frame_trim()
        assert screen.return_value.present.call_args.args[0].trim_android_frame
        assert app.navigate_to.call_count == 2
        view.close()
        count = screen.return_value.present.call_count
        view.request_toggle_android_app_expanded()
        assert screen.return_value.present.call_count == count


def test_frame_crop_sizes_and_offsets_the_borrowed_window_without_scaling():
    embedder = X11WindowEmbedder()
    embedder._window_id = 12
    embedder._host_window_id = 99
    with patch('frontends.x11.x11_window_embedder.subprocess.run', return_value=
               subprocess.CompletedProcess([], 0, stdout='')) as run:
        embedder.set_vertical_crop(56, 48)
        embedder.resize(600, 500)
        commands = [call.args[0] for call in run.call_args_list]
        assert ['xdotool', 'windowsize', '12', '600', '604'] in commands
        assert ['xdotool', 'windowmove', '--', '12', '0', '-56'] in commands
        embedder.clear()
        assert embedder._vertical_crop == (0, 0)


@pytest.mark.parametrize('windows', ['', '12\n13\n'])
def test_surface_rejects_missing_or_ambiguous_compositors(windows):
    with patch('apps.orcUi.adapters.waydroid_surface_player.subprocess.run',
               return_value=Mock(returncode=0, stdout=windows)), patch(
               'apps.orcUi.adapters.waydroid_surface_player.subprocess.Popen') as spawn:
        with pytest.raises(RuntimeError, match='exactly one dedicated Weston'):
            WaydroidSurfacePlayer().play('android', display=':0')
        spawn.assert_not_called()


def test_surface_repeated_open_and_stop_only_own_presentation_clients():
    clients = [Mock(), Mock()]
    for client in clients:
        client.poll.return_value = None
    with patch('apps.orcUi.adapters.waydroid_surface_player.subprocess.run',
               return_value=Mock(returncode=0, stdout='12\n')) as run, patch(
               'apps.orcUi.adapters.waydroid_surface_player.subprocess.Popen',
               side_effect=clients) as spawn:
        player = WaydroidSurfacePlayer()
        assert player.play('android', display=':2')
        player.request_theme_refresh()
        assert spawn.call_count == 1
        assert player.play('android', display=':2')
        clients[0].terminate.assert_called_once()
        player.stop()
        player.stop()
        clients[1].terminate.assert_called_once()
        assert spawn.call_args.args[0] == ['waydroid', 'show-full-ui']
        assert spawn.call_args.kwargs['env']['DISPLAY'] == ':2'
        assert run.call_count == 2


def test_external_surface_detaches_to_x_root_before_orc_window_destruction():
    screen = BrowserMediaScreen('android', Mock(), title='Android', player=Mock(),
                                default_target='android', window_class='Weston Compositor',
                                back_action=Mock(), preserve_external_window=True)
    screen._embedder = Mock(window_id=12)
    screen._embedder.root_window_id.return_value = 42
    screen.hide()
    screen._embedder.detach.assert_called_once_with(42)
    screen._embedder.root_window_id.assert_called_once_with()
    screen._host.screen_parent.winfo_toplevel.assert_not_called()


def test_root_lookup_uses_real_x11_window_identifier():
    with patch('frontends.x11.x11_window_embedder.subprocess.run', return_value=
               subprocess.CompletedProcess(['xwininfo', '-root'], 0,
                   stdout='xwininfo: Window id: 0x50d (the root window) (has no name)')) as run:
        assert X11WindowEmbedder.root_window_id() == 0x50d
        assert run.call_args.args[0] == ['xwininfo', '-root']


def test_root_lookup_failure_is_actionable():
    with patch('frontends.x11.x11_window_embedder.subprocess.run', side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match='x11-utils'):
            X11WindowEmbedder.root_window_id()


def test_failed_external_embed_restores_safe_parent():
    embedder = X11WindowEmbedder(timeout_seconds=0.01)
    def fail_mapping(command, **kwargs):
        if command == ['xdotool', 'windowmap', '12'] and kwargs.get('check'):
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
    with patch.object(embedder, 'supported', return_value=True), patch.object(
            embedder, '_find_by_process', return_value=12), patch.object(
            embedder, 'resize'), patch(
            'frontends.x11.x11_window_embedder.subprocess.run', side_effect=fail_mapping) as run:
        with pytest.raises(RuntimeError, match='no usable X11 window'):
            embedder.embed(0, 99, 800, 400, failure_parent_window_id=42)
        commands = [call.args[0] for call in run.call_args_list]
        assert ['xdotool', 'windowreparent', '12', '42'] in commands
        assert embedder.window_id is None
