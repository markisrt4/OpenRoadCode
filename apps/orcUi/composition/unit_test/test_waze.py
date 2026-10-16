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
def test_platform_config_uses_official_embed_and_dedicated_profile(name):
    from pathlib import Path
    config = ApplicationsConfigParser(Path('config') / name).load()
    app = config.app('waze')
    assert app.url.startswith('https://embed.waze.com/iframe?')
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
        app.register_screen.assert_called_once_with('WAZE', screen, before='NAVIGATION')
        screen_type.call_args.kwargs['back_action']()
        app.navigate_to.assert_called_once_with('HOME')
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
