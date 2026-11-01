# SPDX-License-Identifier: MIT
"""Tests for the native Spotify Connect receiver lifecycle."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from controllers.spotify.librespot_receiver import LibrespotReceiver


def test_missing_binary_is_reported(tmp_path):
    receiver = LibrespotReceiver(executable="missing-librespot", cache_dir=tmp_path)
    with patch("controllers.spotify.librespot_receiver.shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="not found"):
            receiver.start()


def test_offline_does_not_launch(tmp_path):
    receiver = LibrespotReceiver(cache_dir=tmp_path, network_allowed=lambda: False)
    with pytest.raises(RuntimeError, match="offline"):
        receiver.start()


def test_start_stop_and_idempotency(tmp_path):
    process = MagicMock()
    process.poll.return_value = None
    with patch("controllers.spotify.librespot_receiver.shutil.which", return_value="/usr/bin/librespot"), patch(
        "controllers.spotify.librespot_receiver.subprocess.Popen", return_value=process
    ) as popen:
        receiver = LibrespotReceiver(cache_dir=tmp_path, backend="pulseaudio")
        receiver.start()
        receiver.start()
        assert popen.call_count == 1
        args = popen.call_args.args[0]
        assert args[:3] == ["/usr/bin/librespot", "--name", "OpenRoadCode"]
        assert args[-2:] == ["--backend", "pulseaudio"]
        receiver.stop()
        process.terminate.assert_called_once()
        receiver.stop()
        assert process.terminate.call_count == 1
