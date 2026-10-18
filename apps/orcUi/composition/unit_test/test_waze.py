# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Waze owns browser lifetime independently of ORC navigation."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.composition.waze import WazeComposition, configure_waze
from config.application_config import ApplicationsConfigParser
from frontends.tk.media.browser_media_screen import BrowserMediaScreen


@pytest.mark.parametrize('name', ['applications.toml', 'applications.termux.toml'])
def test_platform_config_uses_full_live_map_and_dedicated_profile(name):
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


def test_waze_registration_offline_shutdown_and_back():
    app = Mock()
    runtime = SimpleNamespace(waze_url='https://embed.waze.com/iframe?zoom=12', manager=Mock())
    with patch('apps.orcUi.composition.waze.BrowserMediaScreen') as screen_type:
        composition = configure_waze(app, runtime)
        screen = screen_type.return_value
        app.register_screen.assert_called_once_with('WAZE', screen, show_in_navigation=False)
        screen_type.call_args.kwargs['back_action']()
        app.navigate_to.assert_called_once_with('NAVIGATION')
        on_mode = app.online_mode.subscribe.call_args.args[0]
        on_mode(True)
        screen.hide.assert_not_called()
        on_mode(False)
        screen.hide.assert_called_once()
        composition.close()
        composition.close()
        app.online_mode.subscribe.return_value.assert_called_once_with()
        assert screen.hide.call_count == 2


def test_registration_failure_cleans_subscription_and_screen():
    app = Mock()
    app.register_screen.side_effect = RuntimeError('registration failed')
    runtime = SimpleNamespace(waze_url='https://embed.waze.com/iframe', manager=Mock())
    with patch('apps.orcUi.composition.waze.BrowserMediaScreen') as screen_type:
        with pytest.raises(RuntimeError, match='registration failed'):
            configure_waze(app, runtime)
        app.online_mode.subscribe.return_value.assert_called_once_with()
        screen_type.return_value.hide.assert_called_once()


def test_close_still_hides_when_unsubscribe_fails():
    screen = Mock()
    composition = WazeComposition(screen, Mock(side_effect=RuntimeError('unsubscribe failed')))
    with pytest.raises(RuntimeError, match='unsubscribe failed'):
        composition.close()
    composition.close()
    screen.hide.assert_called_once()


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
def test_runtime_registers_only_enabled_waze_and_preserves_configured_url(enabled):
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
        assert ('waze' in keys) is (enabled is True)
        assert runtime.waze_url == (url if enabled else None)
        runtime.close()
        manager.stop_all.assert_called_once()


def test_open_request_checks_online_mode_and_ignores_requests_after_close():
    app = Mock()
    runtime = SimpleNamespace(waze_url='https://embed.waze.com/iframe', manager=Mock())
    with patch('apps.orcUi.composition.waze.BrowserMediaScreen'):
        composition = configure_waze(app, runtime)
        app.online_mode.online = False
        composition.request_open_waze()
        app.navigate_to.assert_not_called()
        app.online_mode.online = True
        composition.request_open_waze()
        app.navigate_to.assert_called_once_with('WAZE')
        composition.close()
        composition.request_open_waze()
        app.navigate_to.assert_called_once_with('WAZE')


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


def test_waze_composition_supplies_current_orc_color_scheme_to_browser_and_controller():
    from ui.theme import ThemeMode
    app = Mock()
    app.theme_mode = ThemeMode.DARK
    runtime = SimpleNamespace(waze_url='https://www.waze.com/live-map', manager=Mock())
    with patch('apps.orcUi.composition.waze.ManagedBrowserMediaPlayer') as player, patch(
        'apps.orcUi.composition.waze.WazeLocationPlayer') as location, patch(
        'apps.orcUi.composition.waze.BrowserMediaScreen') as screen:
        configure_waze(app, runtime)
        preference = player.call_args.kwargs['preferred_color_scheme']
        assert preference() == 'dark'
        app.theme_mode = ThemeMode.LIGHT
        assert preference() == 'light'
        assert location.call_args.kwargs['preferred_color_scheme'] is preference
        assert screen.call_args.kwargs['theme_request_handler'] is location.return_value


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
