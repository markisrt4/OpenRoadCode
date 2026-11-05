# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
import json
import subprocess
from unittest.mock import Mock, patch

from apps.orcUi.adapters.scrcpy_waze_gestures import ScrcpyWazeGestures
from ui.navigation.waze_gesture_if import WazeGesture


def surface():
    player = Mock()
    player.gesture_surface.return_value = (object(), 'owned-unique-viewer', (1280, 720), ':1')
    return player, Mock(window_id=123)


def test_sender_targets_only_the_owned_viewer_without_adb_or_global_input_commands():
    player, embedder = surface()
    with patch('apps.orcUi.adapters.scrcpy_waze_gestures.subprocess.Popen') as spawn:
        process = spawn.return_value
        process.communicate.return_value = ('', '')
        process.returncode = 0
        process.poll.return_value = 0
        ScrcpyWazeGestures(player, embedder).perform(WazeGesture.PAN_UP, lambda: False)
    payload = json.loads(process.communicate.call_args.kwargs['input'])
    assert payload == dict(window=123, title='owned-unique-viewer', frame_size=[1280, 720], gesture='pan-up')
    assert spawn.call_args.args[0][-1] == 'frontends.x11.scrcpy_gesture_sender'
    assert spawn.call_args.kwargs['env']['DISPLAY'] == ':1'


def test_hidden_missing_or_cancelled_targets_never_start_a_sender():
    player, embedder = surface()
    with patch('apps.orcUi.adapters.scrcpy_waze_gestures.subprocess.Popen') as spawn:
        adapter = ScrcpyWazeGestures(player, embedder)
        adapter.perform(WazeGesture.ZOOM_IN, lambda: True)
        embedder.window_id = None
        adapter.perform(WazeGesture.ZOOM_IN, lambda: False)
        assert not adapter.available
    spawn.assert_not_called()


def test_session_change_cancels_sender_and_allows_its_input_cleanup():
    player, embedder = surface()
    original = player.gesture_surface.return_value
    player.gesture_surface.side_effect = [original, original, (object(), 'new-session', (1280, 720), ':1')]
    with patch('apps.orcUi.adapters.scrcpy_waze_gestures.subprocess.Popen') as spawn:
        process = spawn.return_value
        process.communicate.side_effect = [subprocess.TimeoutExpired('sender', .05), ('', '')]
        process.poll.return_value = None
        ScrcpyWazeGestures(player, embedder).perform(WazeGesture.ZOOM_IN, lambda: False)
        process.terminate.assert_called_once_with()
