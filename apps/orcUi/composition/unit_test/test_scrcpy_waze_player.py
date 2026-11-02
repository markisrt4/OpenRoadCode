# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import subprocess
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.adapters.scrcpy_waze_player import ScrcpyWazePlayer
from apps.launchers.scrcpy_waze_launcher import ScrcpyWazeLauncher


def test_viewer_uses_native_waze_virtual_display_and_requested_x11(tmp_path, monkeypatch):
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    monkeypatch.setenv('ORC_SCRCPY_RENDERER', 'software')
    player = ScrcpyWazePlayer()
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.Popen') as spawn, \
            patch('apps.orcUi.adapters.scrcpy_waze_player.Thread') as worker:
        process = spawn.return_value
        process.poll.return_value = None
        assert player.play('android', display=':1', window_size=(900, 500))
        command = spawn.call_args.args[0]
        assert '--new-display=1280x720/240' in command
        assert '--start-app=com.waze' in command
        assert '--render-driver=software' in command
        assert '--no-audio' in command
        assert f'--window-title={player.window_name}' in command
        assert spawn.call_args.kwargs['env']['DISPLAY'] == ':1'
        assert spawn.call_args.kwargs['env']['SDL_VIDEODRIVER'] == 'x11'
        player.request_theme_refresh()
        assert spawn.call_count == 1
        player.stop()
        player.stop()
        process.wait.assert_not_called()
        assert worker.call_count == 1
        worker.call_args.kwargs['target'](*worker.call_args.kwargs['args'])
        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=3)
    assert (tmp_path / 'orc-scrcpy-waze.log').exists()
    assert player.vertical_crop() == (0, 0)


def test_unresponsive_owned_viewer_is_killed_without_adb_commands():
    player = ScrcpyWazePlayer()
    process = player._process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired('scrcpy', 3), None]
    with patch('apps.orcUi.adapters.scrcpy_waze_player.Thread') as worker:
        player.stop()
        process.wait.assert_not_called()
        worker.call_args.kwargs['target'](*worker.call_args.kwargs['args'])
    process.terminate.assert_called_once_with()
    process.kill.assert_called_once_with()
    assert player._process is None


def test_invalid_renderer_never_starts_viewer(monkeypatch):
    monkeypatch.setenv('ORC_SCRCPY_RENDERER', 'unexpected')
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.Popen') as spawn:
        with pytest.raises(ValueError, match='ORC_SCRCPY_RENDERER'):
            ScrcpyWazePlayer().play('android', display=':1')
    spawn.assert_not_called()


def test_missing_or_ambiguous_adb_device_does_not_start_native_view():
    with patch('apps.launchers.scrcpy_waze_launcher.subprocess.run') as run:
        run.return_value = subprocess.CompletedProcess([], 1, '', 'more than one device')
        assert ScrcpyWazeLauncher().launch_installed_app('com.waze') is None
        run.return_value = subprocess.CompletedProcess([], 0, 'package:/data/app/waze/base.apk', '')
        assert ScrcpyWazeLauncher().launch_installed_app('com.waze') == 'Waze'
        assert run.call_args.args[0] == ['adb', 'shell', 'pm', 'path', 'com.waze']


def test_fast_reopen_has_a_new_window_identity_while_old_viewer_retires(tmp_path, monkeypatch):
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    player = ScrcpyWazePlayer()
    old_process, new_process = Mock(), Mock()
    old_process.poll.return_value = None
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.Popen',
               side_effect=[old_process, new_process]), \
            patch('apps.orcUi.adapters.scrcpy_waze_player.Thread') as worker:
        player.play('android', display=':1')
        first_name = player.window_name
        player.stop()
        player.play('android', display=':1')
        assert player.window_name != first_name
        worker.call_args.kwargs['target'](*worker.call_args.kwargs['args'])
        new_process.terminate.assert_not_called()
        assert player._process is new_process
