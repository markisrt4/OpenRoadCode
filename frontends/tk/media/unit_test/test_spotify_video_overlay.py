# SPDX-License-Identifier: MIT

"""Native host retirement and semantic return behavior without X11."""

from unittest.mock import Mock

from frontends.tk.media.spotify_video_overlay import SpotifyVideoOverlay


def test_close_detaches_before_host_destruction():
    events = []
    parent, native = Mock(), Mock()
    native.window_id = 123
    parent.winfo_toplevel.return_value.winfo_id.return_value = 456
    native.detach.side_effect = lambda _parent: events.append("detach")
    overlay = SpotifyVideoOverlay(parent, native_surface=native, set_status=Mock())
    frame = Mock()
    frame.destroy.side_effect = lambda: events.append("destroy")
    overlay._overlay = frame
    overlay.close()
    assert events == ["detach", "destroy"]
    native.detach.assert_called_once_with(456)
    assert not overlay.visible


def test_return_emits_semantic_request_after_detachment():
    events = []
    native = Mock()
    native.window_id = None
    overlay = SpotifyVideoOverlay(Mock(), native_surface=native, set_status=Mock())
    frame = Mock()
    frame.destroy.side_effect = lambda: events.append("destroy")
    overlay._overlay = frame
    handler = Mock()
    handler.request_return_to_spotify.side_effect = lambda: events.append("request")
    overlay.set_video_request_handler(handler)
    overlay.return_to_spotify()
    assert events == ["destroy", "request"]


def test_detach_failure_still_retires_overlay():
    native = Mock()
    native.window_id = 123
    native.detach.side_effect = RuntimeError("gone")
    parent = Mock()
    parent.winfo_toplevel.return_value.winfo_id.return_value = 456
    overlay = SpotifyVideoOverlay(parent, native_surface=native, set_status=Mock())
    frame = Mock()
    overlay._overlay = frame
    overlay.close()
    native.clear.assert_called_once_with()
    frame.destroy.assert_called_once_with()
