# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import subprocess
from unittest.mock import Mock, patch

from apps.launchers.scrcpy_business_app_launcher import ScrcpyBusinessAppLauncher
from apps.orcUi.composition.business_apps import configure_termux_business_apps


def test_business_embedding_composes_its_own_player_and_maps_only_curated_packages():
    with patch('apps.orcUi.composition.business_apps.ScrcpyAppPlayer') as player, \
            patch('apps.orcUi.composition.business_apps.AndroidAppView') as view, \
            patch('apps.orcUi.composition.business_apps.X11WindowEmbedder'):
        result, launcher = configure_termux_business_apps(Mock(), map_runtime=Mock(),
            map_platform=Mock(), map_presentation=Mock())
        assert result is view.return_value
        assert view.call_args.kwargs['player'] is player.return_value
        assert view.call_args.kwargs['prepare_app'] == player.return_value.prepare_package
        assert view.call_args.kwargs['full_width_apps'] is True
        with patch('apps.launchers.scrcpy_business_app_launcher.subprocess.run', return_value=
                   subprocess.CompletedProcess([], 0, 'package:/data/app/panera/base.apk', '')):
            assert launcher.launch_installed_app('com.panera.bread') == 'Panera Bread'
            assert launcher.launch_installed_app('com.waze') is None
        launcher.stop_installed_app('com.panera.bread')
        player.return_value.stop.assert_called_once_with()


def test_unknown_or_missing_app_never_starts_an_activity_on_the_phone_display():
    launcher = ScrcpyBusinessAppLauncher({'com.panera.bread': 'Panera'})
    with patch('apps.launchers.scrcpy_business_app_launcher.subprocess.run') as run:
        assert launcher.launch_installed_app('com.unknown.app') is None
        assert launcher.launch_installed_app('com.panera.bread', uri='https://example.com') is None
        malformed = ScrcpyBusinessAppLauncher({'com.example;bad': 'Bad package'})
        assert malformed.launch_installed_app('com.example;bad') is None
        run.assert_not_called()
        run.return_value = subprocess.CompletedProcess([], 1, '', 'device offline')
        assert launcher.launch_installed_app('com.panera.bread') is None
        assert run.call_args.args[0] == ['adb', 'shell', 'pm', 'path', 'com.panera.bread']
