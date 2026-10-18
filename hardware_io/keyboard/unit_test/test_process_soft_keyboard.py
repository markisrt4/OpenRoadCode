# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Own only an explicitly configured system keyboard process."""
from unittest.mock import Mock, patch
import subprocess

import pytest

from hardware_io.keyboard.process_soft_keyboard import ProcessSoftKeyboard


@pytest.mark.parametrize('command', ['', 'keyboard --flag', [], [''], ['keyboard', '\0'], [1]])
def test_requires_argument_sequence_without_shell_parsing(command):
    with pytest.raises(ValueError):
        ProcessSoftKeyboard(command)


def test_constructor_is_inert_and_missing_keyboard_is_reported():
    with patch('hardware_io.keyboard.process_soft_keyboard.shutil.which', return_value=None), patch(
        'hardware_io.keyboard.process_soft_keyboard.subprocess.Popen') as spawn:
        keyboard = ProcessSoftKeyboard(['missing-keyboard'])
        assert not keyboard.available
        with pytest.raises(RuntimeError, match='not installed'):
            keyboard.show()
        spawn.assert_not_called()
        keyboard.hide()
        keyboard.close()


def test_reuses_own_process_inherits_environment_and_releases_it_once():
    process = Mock()
    process.poll.return_value = None
    with patch('hardware_io.keyboard.process_soft_keyboard.shutil.which', return_value='/usr/bin/keyboard'), patch(
        'hardware_io.keyboard.process_soft_keyboard.subprocess.Popen', return_value=process) as spawn, patch.dict(
        'os.environ', {'DISPLAY': ':0', 'ORC_INPUT_TEST': 'kept'}):
        keyboard = ProcessSoftKeyboard(['keyboard', '--foreground'], display=':1')
        spawn.assert_not_called()
        keyboard.show()
        keyboard.show()
        spawn.assert_called_once()
        assert spawn.call_args.args[0] == ('/usr/bin/keyboard', '--foreground')
        assert spawn.call_args.kwargs['env']['DISPLAY'] == ':1'
        assert spawn.call_args.kwargs['env']['ORC_INPUT_TEST'] == 'kept'
        assert 'shell' not in spawn.call_args.kwargs
        keyboard.close()
        keyboard.close()
        process.terminate.assert_called_once()
        process.wait.assert_called_once_with(timeout=0.5)
        assert not keyboard.available
        with pytest.raises(RuntimeError, match='closed'):
            keyboard.show()


def test_early_exit_is_not_claimed_as_a_visible_keyboard():
    process = Mock()
    process.poll.return_value = 0
    with patch('hardware_io.keyboard.process_soft_keyboard.shutil.which', return_value='/usr/bin/keyboard'), patch(
        'hardware_io.keyboard.process_soft_keyboard.subprocess.Popen', return_value=process):
        keyboard = ProcessSoftKeyboard(['keyboard'])
        with pytest.raises(RuntimeError, match='exited during startup'):
            keyboard.show()
        keyboard.close()
        process.terminate.assert_not_called()


def test_hung_owned_process_is_killed_and_reaped():
    process = Mock()
    process.poll.return_value = None
    process.wait.side_effect = [subprocess.TimeoutExpired('keyboard', 0.5), 0]
    with patch('hardware_io.keyboard.process_soft_keyboard.shutil.which', return_value='/usr/bin/keyboard'), patch(
        'hardware_io.keyboard.process_soft_keyboard.subprocess.Popen', return_value=process):
        keyboard = ProcessSoftKeyboard(['keyboard'])
        keyboard.show()
        keyboard.hide()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        assert process.wait.call_count == 2
        keyboard.close()
        assert process.wait.call_count == 2
