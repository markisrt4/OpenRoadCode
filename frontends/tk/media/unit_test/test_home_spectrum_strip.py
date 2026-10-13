# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
from unittest.mock import Mock

from frontends.tk.media.home_spectrum_strip import HomeSpectrumStrip
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumState


def test_visibility_releases_capture_and_stale_data_keeps_start_stop_available():
    view = object.__new__(HomeSpectrumStrip)
    view._closed = False
    view._attached = False
    view._feed = Mock()
    view._button = Mock()
    view._host = Mock()
    view._host.winfo_viewable.return_value = True
    view._feed.read_spectrum.return_value = HomeSpectrumState((0.1, 0.8), True, running=True)
    for name in ('delete', 'after', 'create_rectangle', 'create_text', 'cget', 'winfo_rgb'):
        setattr(view, name, Mock())
    view.winfo_width = Mock(return_value=280)
    view.winfo_height = Mock(return_value=68)
    view.cget.return_value = "#101010"
    view.winfo_rgb.return_value = (4096, 4096, 4096)
    view._paint()
    view._feed.attach_home.assert_called_once()
    assert view.create_rectangle.call_count == 24
    view._feed.read_spectrum.return_value = HomeSpectrumState()
    view._paint()
    assert view.create_rectangle.call_count > 24
    assert view._button.configure.call_args.kwargs['text'] == '▶ Spectrum'
    view._host.winfo_viewable.return_value = False
    view._paint()
    view._paint()
    view._feed.detach_home.assert_called_once()
    assert view._feed.read_spectrum.call_count == 2


def test_button_emits_capture_requests_separately_from_playback():
    view = object.__new__(HomeSpectrumStrip)
    view._closed = False
    view._feed = Mock()
    view._running = False
    view._request_toggle()
    view._feed.request_start_spectrum.assert_called_once()
    view._running = True
    view._request_toggle()
    view._feed.request_stop_spectrum.assert_called_once()
    view._closed = True
    view._request_toggle()
    assert view._feed.request_stop_spectrum.call_count == 1
