# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import subprocess
import shlex
from unittest.mock import Mock, patch

import pytest

from apps.orcUi.adapters.scrcpy_waze_player import ScrcpyWazePlayer
from apps.launchers.scrcpy_waze_launcher import ScrcpyWazeLauncher


def test_retained_viewer_returns_without_restarting_process_or_changing_window_identity():
    player = ScrcpyWazePlayer(retain_session=True)
    process = player._process = Mock()
    process.poll.return_value = None
    identity = player.window_name
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.Popen') as spawn:
        player.play('android', display=':1')
        player.play('android', display=':1')
    spawn.assert_not_called()
    process.terminate.assert_not_called()
    assert player.window_name == identity


def test_explicit_close_stops_android_waze_before_releasing_owned_viewer():
    stop = Mock()
    launcher = ScrcpyWazeLauncher(stop_viewer=stop)
    with patch('apps.launchers.scrcpy_waze_launcher.subprocess.run', return_value=
               subprocess.CompletedProcess([], 0, '', '')) as run:
        launcher.stop_installed_app('com.waze')
    assert run.call_args.args[0] == ['adb', 'shell', 'am', 'force-stop', 'com.waze']
    stop.assert_called_once_with()


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
        assert '--new-display=1296x720/240' in command
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


@pytest.mark.parametrize('size', [(876, 383), (522, 184), (1280, 720)])
def test_virtual_display_matches_panel_aspect_without_reducing_android_resolution(size, tmp_path, monkeypatch):
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.Popen') as spawn:
        ScrcpyWazePlayer().play('android', display=':1', window_size=size)
    command = spawn.call_args.args[0]
    option = next(value for value in command if value.startswith('--new-display='))
    width, height = map(int, option.split('=')[1].split('/')[0].split('x'))
    assert width >= 1280 and height >= 720
    assert width % 2 == height % 2 == 0
    assert abs(width / height - size[0] / size[1]) < .003


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


def test_destination_waits_for_current_display_and_quotes_uri_for_android_shell(tmp_path):
    path = tmp_path / 'scrcpy.log'
    old = b'[server] INFO: New display: 1280x720/240 (id=6)\n'
    path.write_bytes(old + b'[server] INFO: New display: 1280x720/240 (id=17)\n')
    process, cancelled = Mock(), Mock()
    process.poll.return_value = None
    cancelled.wait.return_value = False
    cancelled.is_set.return_value = False
    uri = 'waze://?ll=42.5,-83.25&navigate=yes'
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.run', return_value=
               subprocess.CompletedProcess([], 0, 'Starting: Intent', '')) as run:
        ScrcpyWazePlayer._deliver_destination(process, cancelled, uri, path, len(old))
    command = run.call_args.args[0]
    assert command[:2] == ['adb', 'shell']
    assert shlex.split(command[2]) == ['am', 'start', '--display', '17',
        '-a', 'android.intent.action.VIEW', '-d', uri, '-p', 'com.waze']


def test_cancelled_destination_never_uses_phone_default_display(tmp_path):
    process, cancelled = Mock(), Mock()
    cancelled.wait.return_value = True
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.run') as run:
        ScrcpyWazePlayer._deliver_destination(process, cancelled, 'waze://?', tmp_path / 'missing', 0)
    run.assert_not_called()


def test_no_display_acknowledgement_reports_failure_instead_of_sending_to_phone(tmp_path, caplog):
    path = tmp_path / 'scrcpy.log'
    path.write_bytes(b'waiting for Android\n')
    process, cancelled = Mock(), Mock()
    process.poll.return_value = None
    cancelled.wait.return_value = False
    cancelled.is_set.return_value = False
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.run') as run:
        ScrcpyWazePlayer._deliver_destination(process, cancelled, 'waze://?', path, 0)
    run.assert_not_called()
    assert 'Could not deliver' in caplog.text


def test_launcher_queues_destination_only_after_confirming_package():
    prepare = Mock()
    launcher = ScrcpyWazeLauncher(prepare_destination=prepare)
    uri = 'waze://?ll=42,-83&navigate=yes'
    with patch('apps.launchers.scrcpy_waze_launcher.subprocess.run') as run:
        run.return_value = subprocess.CompletedProcess([], 0, 'package:/data/app/waze/base.apk', '')
        assert launcher.launch_installed_app('com.waze', uri=uri) == 'Waze'
        prepare.assert_called_once_with(uri)
        launcher.launch_installed_app('com.waze')
        prepare.assert_called_with(None)


def test_viewer_launch_starts_destination_worker_with_current_log_offset(tmp_path, monkeypatch):
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    path = tmp_path / 'orc-scrcpy-waze.log'
    path.write_bytes(b'old viewer log\n')
    player = ScrcpyWazePlayer()
    uri = 'waze://?ll=42,-83&navigate=yes'
    player.prepare_destination(uri)
    with patch('apps.orcUi.adapters.scrcpy_waze_player.subprocess.Popen') as spawn, \
            patch('apps.orcUi.adapters.scrcpy_waze_player.Thread') as worker:
        player.play('android', display=':1')
        args = worker.call_args.kwargs['args']
        assert args[0] is spawn.return_value
        assert args[2:] == (uri, path, len(b'old viewer log\n'))
        assert not args[1].is_set()
        player.stop()
        assert args[1].is_set()
