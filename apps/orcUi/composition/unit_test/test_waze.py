# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Native Waze composition and shared hosted-surface lifecycle."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.waze import WazeComposition, configure_waze
from config.application_config import ApplicationsConfigParser
from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from ui.navigation import GeoPoint


def test_missing_android_backend_reports_unavailable_without_constructing_browser():
    app = Mock()
    runtime = SimpleNamespace(waze_url='https://www.waze.com/live-map', manager=Mock())
    composition = configure_waze(app, runtime)
    entry = app.register_screen.call_args.args[1]
    entry.show()
    composition.request_navigate_waze(GeoPoint(.7, -1.4))
    assert 'Native Waze is not configured' in app.set_screen_status.call_args.args[0]
    assert runtime.manager.mock_calls == []
    app.navigate_to.assert_not_called()
    assert app.register_screen.call_count == 1
    assert app.register_screen.call_args.args[0] == 'WAZE'
    composition.close()
    app.set_screen_status.reset_mock()
    composition.request_open_waze()
    app.set_screen_status.assert_not_called()


def test_native_failure_cannot_fall_back_to_chrome():
    app, view = Mock(), Mock()
    runtime = SimpleNamespace(waze_url='https://www.waze.com/live-map', manager=Mock())
    with patch('apps.orcUi.composition.waze.WazeAppController') as native:
        composition = configure_waze(app, runtime, android_app_view=view)
        composition.request_open_waze()
        native.return_value.request_open_waze.assert_called_once_with()
        native.call_args.kwargs['fallback']()
        assert 'Native Waze unavailable' in app.set_screen_status.call_args.args[0]
        app.navigate_to.assert_not_called()
        assert runtime.manager.mock_calls == []
        app.online_mode.subscribe.call_args.args[0](False)
        native.return_value.cancel.assert_called_once_with()
        composition.close()
        composition.close()
        native.return_value.close.assert_called_once_with()
        app.online_mode.subscribe.return_value.assert_called_once_with()


def test_destination_and_termux_adapter_are_forwarded_to_native_session():
    app, view, launcher = Mock(), Mock(), Mock()
    runtime = SimpleNamespace(waze_url='legacy-url-is-not-a-browser-target', manager=Mock())
    with patch('apps.orcUi.composition.waze.WazeAppController') as native:
        composition = configure_waze(app, runtime, android_app_view=view, native_launcher=launcher)
        assert native.call_args.args == (launcher, view)
        point = GeoPoint(.7, -1.4)
        composition.request_navigate_waze(point)
        native.return_value.request_navigate_waze.assert_called_once_with(point)
        composition.request_close_waze()
        native.return_value.request_close_waze.assert_called_once_with()
        composition.close()
        composition.request_navigate_waze(point)
        native.return_value.request_navigate_waze.assert_called_once_with(point)


def test_native_registration_failure_releases_subscription_and_controller():
    app = Mock()
    app.register_screen.side_effect = RuntimeError('registration failed')
    with patch('apps.orcUi.composition.waze.WazeAppController') as native:
        with pytest.raises(RuntimeError, match='registration failed'):
            configure_waze(app, SimpleNamespace(waze_url='enabled'), android_app_view=Mock())
        native.return_value.close.assert_called_once_with()
        app.online_mode.subscribe.return_value.assert_called_once_with()


def test_failed_unsubscribe_does_not_skip_native_shutdown():
    native = Mock()
    composition = WazeComposition(Mock(side_effect=RuntimeError('unsubscribe failed')), native=native)
    with pytest.raises(RuntimeError, match='unsubscribe failed'):
        composition.close()
    composition.close()
    native.close.assert_called_once_with()

def test_hidden_retained_surface_unmaps_but_does_not_stop_player_until_close():
    host, player, embedder = Mock(), Mock(), Mock(window_id=12)
    embedder.root_window_id.return_value = 42
    screen = BrowserMediaScreen('waze', host, title='Waze', player=player,
        default_target='android', window_class='Weston Compositor', back_action=Mock(),
        keep_player_on_hide=True, window_embedder=embedder)
    screen.hide()
    embedder.detach.assert_called_once_with(42)
    player.stop.assert_not_called()
    embedder.window_id = None
    screen.close_session()
    player.stop.assert_called_once_with()


@pytest.mark.parametrize('name', ['applications.toml', 'applications.termux.toml'])
def test_legacy_waze_enable_config_remains_compatible(name):
    from pathlib import Path
    config = ApplicationsConfigParser(Path('config') / name).load()
    app = config.app('waze')
    assert app.url == 'https://www.waze.com/live-map'
    assert app.profile == 'waze'
    assert app.startup.value == 'lazy'
    assert config.target_for_app(app) == config.target('primary')


def test_custom_config_without_waze_does_not_register_screen():
    app = Mock()
    assert configure_waze(app, SimpleNamespace(waze_url=None)) is None
    app.register_screen.assert_not_called()
    app.online_mode.subscribe.assert_not_called()


def test_hidden_browser_cancels_pending_launch_and_ignores_late_callback():
    app, player = Mock(), Mock()
    with patch('frontends.tk.media.browser_media_screen.X11WindowEmbedder') as embedder:
        embedder.return_value.window_id = None
        screen = BrowserMediaScreen('waze', app, title='Waze', player=player,
            default_target='https://embed.waze.com/iframe', window_class='openroadcode-waze',
            back_action=Mock())
        screen._launch_job = 'pending-launch'
        screen._browser_host = Mock()
        screen.hide()
        screen._launch_and_embed()
        app.cancel_ui_callback.assert_called_once_with('pending-launch')
        player.stop.assert_called_once()
        player.play.assert_not_called()
        embedder.return_value.embed.assert_not_called()


@pytest.mark.parametrize('enabled', [None, False, True])
def test_runtime_keeps_enable_setting_but_never_registers_a_waze_browser(enabled):
    from contextlib import ExitStack
    from apps.orcUi.application_runtime import create_orc_ui_application_runtime

    names = ('ApplicationsConfigParser', 'AppRuntimeManager', 'ManagedSDRPPLauncher',
             'BrowserApplicationFactory', 'GoogleEarthLauncher', 'StreamingRadioController',
             'MpvStreamingAudioPlayer', 'MediaApplicationService', 'create_spotify_controller')
    with ExitStack() as stack:
        factories = {name: stack.enter_context(patch(f'apps.orcUi.application_runtime.{name}'))
                     for name in names}
        config = factories['ApplicationsConfigParser'].return_value.load.return_value
        config.app.side_effect = lambda key: Mock(enabled=False, fullscreen=False)
        url = 'https://embed.waze.com/iframe?zoom=10&lat=51&lon=0'
        config.apps = (() if enabled is None else
                       (SimpleNamespace(key='waze', enabled=enabled, url=url),))
        runtime = create_orc_ui_application_runtime()
        manager = factories['AppRuntimeManager'].return_value
        keys = [call.args[0] for call in manager.register.call_args_list]
        assert 'waze' not in keys
        assert not any(c.args == ('waze',) for c in factories['BrowserApplicationFactory'].return_value.create.call_args_list)
        assert runtime.waze_url == (url if enabled else None)
        runtime.close()
        manager.stop_all.assert_called_once()


def test_cancelled_browser_launch_does_not_attempt_embedding():
    app, player, surface = Mock(), Mock(), Mock()
    player.play.return_value = False
    surface.winfo_width.return_value = 800
    surface.winfo_height.return_value = 480
    with patch('frontends.tk.media.browser_media_screen.X11WindowEmbedder') as embedder:
        screen = BrowserMediaScreen('waze', app, title='Waze', player=player,
            default_target='https://embed.waze.com/iframe', window_class='openroadcode-waze',
            back_action=Mock())
        screen._browser_host = surface
        screen._launch_and_embed()
        embedder.return_value.embed.assert_not_called()
        app.set_screen_status.assert_called_once_with('Waze unavailable')


def test_embedding_resolves_new_viewer_identity_after_player_launch():
    app, player, surface, embedder = Mock(), Mock(), Mock(), Mock(window_id=None)
    identity = ['retired-viewer']
    player.play.side_effect = lambda *args, **kwargs: identity.__setitem__(0, 'current-viewer') or True
    surface.winfo_width.return_value = 800
    surface.winfo_height.return_value = 480
    surface.winfo_id.return_value = 100
    screen = BrowserMediaScreen('waze', app, title='Waze', player=player,
        default_target='android', window_class=None, window_name=lambda: identity[0],
        back_action=Mock(), window_embedder=embedder)
    screen._browser_host = surface
    screen._launch_and_embed()
    assert embedder.embed.call_args.kwargs['window_name'] == 'current-viewer'


def test_embedding_failure_stops_spawned_browser_and_keeps_real_error():
    app, player, surface = Mock(), Mock(), Mock()
    player.play.return_value = True
    surface.winfo_width.return_value = 800
    surface.winfo_height.return_value = 480
    surface.winfo_id.return_value = 100
    with patch('frontends.tk.media.browser_media_screen.X11WindowEmbedder') as embedder:
        embedder.return_value.embed.side_effect = RuntimeError('window not found')
        screen = BrowserMediaScreen('waze', app, title='Waze', player=player,
            default_target='https://embed.waze.com/iframe', window_class='openroadcode-waze',
            back_action=Mock())
        screen._browser_host = surface
        screen._launch_and_embed()
        player.stop.assert_called_once()
        embedder.return_value.clear.assert_called_once()
        app.set_screen_status.assert_called_once_with('Waze launch failed: window not found')


def test_waze_theme_update_preserves_browser_and_route_instead_of_restarting():
    from ui.theme import ThemeMode
    app, player, handler = Mock(), Mock(), Mock()
    with patch('frontends.tk.media.browser_media_screen.X11WindowEmbedder'):
        screen = BrowserMediaScreen('waze', app, title='Waze', player=player,
            default_target='https://www.waze.com/live-map', window_class='openroadcode-waze',
            back_action=Mock(), theme_request_handler=handler)
        screen._visible = True
        screen._restart_browser_for_theme = Mock()
        screen.set_theme_mode(ThemeMode.DARK)
        handler.request_theme_refresh.assert_called_once()
        screen._restart_browser_for_theme.assert_not_called()
        player.stop.assert_not_called()
        player.play.assert_not_called()
