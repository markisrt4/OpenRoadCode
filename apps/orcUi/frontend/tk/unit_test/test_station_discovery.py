# SPDX-License-Identifier: MIT
"""Headless regression tests for touchscreen station discovery."""

from types import SimpleNamespace
from unittest.mock import Mock

from apps.orcUi.frontend.tk.radio_panel import RadioPanel
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.rf_radio_if import RadioAction, RfRadioState


def panel():
    view = RadioPanel.__new__(RadioPanel)
    view._session = Mock()
    view._state = RfRadioState(
        RadioProfileState("FM", 100_000_000, "WFM", "fm_radio", "FM"), (),
        scan_hits=(94_700_000, 104_300_000),
    )
    view._scan_selected = set()
    view._scan_drag_y = None
    view._scan_dragged = False
    view._scan_canvas = Mock()
    view._scan_canvas.canvasx.side_effect = lambda value: value
    view._scan_canvas.canvasy.side_effect = lambda value: value
    view._render_scan_results = Mock()
    view._scan_status = Mock()
    return view


def test_touch_drag_scrolls_without_selecting():
    view = panel()
    view._scan_touch_start(SimpleNamespace(y=120))
    view._scan_touch_move(SimpleNamespace(y=80))
    view._scan_canvas.find_overlapping.return_value = (4,)
    view._scan_canvas.gettags.return_value = ("frequency_94700000",)
    view._scan_touch_end(SimpleNamespace(x=30, y=80))
    view._scan_canvas.yview_scroll.assert_called()
    assert view._scan_selected == set()
    view._scan_canvas.find_overlapping.assert_not_called()


def test_tap_on_station_selects_it():
    view = panel()
    view._scan_touch_start(SimpleNamespace(y=20))
    view._scan_canvas.find_overlapping.return_value = (7,)
    view._scan_canvas.gettags.return_value = ("frequency_94700000",)
    view._scan_touch_end(SimpleNamespace(x=30, y=20))
    assert view._scan_selected == {94_700_000}
    view._render_scan_results.assert_called_once()


def test_empty_space_does_not_select_nearest_station():
    view = panel()
    view._scan_touch_start(SimpleNamespace(y=180))
    view._scan_canvas.find_overlapping.return_value = ()
    view._scan_touch_end(SimpleNamespace(x=30, y=180))
    assert not view._scan_selected


def test_save_requests_presets_and_keeps_results_open():
    view = panel()
    view._scan_selected = {94_700_000, 104_300_000}
    view._save_scanned_presets()
    requests = [call.args[0] for call in view._session.request.call_args_list]
    assert [request.action for request in requests] == [
        RadioAction.ADD_PRESET, RadioAction.ADD_PRESET
    ]
    assert [request.frequency_hz for request in requests] == [
        94_700_000, 104_300_000
    ]
    assert view._scan_selected == set()
    view._scan_status.configure.assert_called_once()
    view._render_scan_results.assert_called_once()
