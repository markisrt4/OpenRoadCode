# SPDX-License-Identifier: MIT
"""Test native visualization controls without requiring a Tk display."""

from collections import deque
from unittest.mock import Mock

from apps.orcUi.frontend.tk.sdrforge_receiver_view import SdrForgeReceiverView


def _view():
    view = object.__new__(SdrForgeReceiverView)
    view._waterfall_enabled = True
    view._peak_hold_enabled = False
    view._bins = (0.2, 0.8)
    view._peak_bins = (0.2, 0.8)
    view._history = deque([(0.1, 0.7)])
    view._db_floor = -90.0
    view._db_ceiling = -20.0
    view._center_frequency_hz = 100_000_000
    view._sample_rate_hz = 2_400_000
    view._viewport = None
    view._gl_surface = None
    view._schedule_render = Mock()
    return view


def test_waterfall_and_peak_hold_preferences():
    view = _view()
    view.set_display_controls(waterfall=False, peak_hold=True)
    assert not view._waterfall_enabled
    assert view._peak_hold_enabled
    assert view._peak_bins == view._bins
    view._schedule_render.assert_called_once()


def test_auto_range_clears_scaling_only():
    view = _view()
    view.auto_range()
    assert view._db_floor is None
    assert view._db_ceiling is None
    assert view._bins == (0.2, 0.8)
    assert len(view._history) == 1


def test_stop_clears_cached_spectrum_and_history():
    view = _view()
    view.clear_spectrum()
    assert view._bins == ()
    assert view._peak_bins == ()
    assert not view._history
    assert view._db_floor is None
    assert view._db_ceiling is None
    assert view._center_frequency_hz is None
