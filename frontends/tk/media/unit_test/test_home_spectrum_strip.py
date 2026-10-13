# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
from unittest.mock import Mock

from frontends.tk.media.home_spectrum_strip import HomeSpectrumStrip
from ui.music_visualizer.home_spectrum_ui_if import HomeSpectrumState


def test_visibility_releases_capture_and_stale_data_hides_strip():
    view = object.__new__(HomeSpectrumStrip)
    view._closed = False
    view._attached = False
    view._feed = Mock()
    view._host = Mock()
    view._host.winfo_viewable.return_value = True
    view._feed.read_spectrum.return_value = HomeSpectrumState((0.1, 0.8), True)
    for name in ('delete', 'pack', 'pack_forget', 'after', 'create_rectangle'):
        setattr(view, name, Mock())
    view._paint()
    view._feed.attach_home.assert_called_once()
    assert view.create_rectangle.call_count == 8
    view._feed.read_spectrum.return_value = HomeSpectrumState()
    view._paint()
    view.pack_forget.assert_called_once()
    view._host.winfo_viewable.return_value = False
    view._paint()
    view._paint()
    view._feed.detach_home.assert_called_once()
    assert view._feed.read_spectrum.call_count == 2
