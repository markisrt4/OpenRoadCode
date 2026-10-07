# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Data health must distinguish empty images from unavailable and stale imagery."""
from unittest.mock import Mock

from controllers.weather.radar_replay_controller import RadarReplayController
from controllers.weather.radar_tile_status import RadarTileStatus
from ui.weather.radar_ui_if import RadarPalette
from ui.weather.radar_ui_stub import RadarUiStub


def replay(tiles=RadarTileStatus(), *, forecast=False):
    backend = Mock(enabled=True, frame_time=1000, frame_times=(900, 1000), frame_index=1,
                   palette=RadarPalette.UNIVERSAL, is_forecast=forecast, frame_tile_status=tiles)
    controller = RadarReplayController(Mock(), RadarUiStub(), backend)
    controller._clock = lambda: 1100
    return controller


def test_empty_tiles_are_not_reported_as_missing_or_dry_weather():
    controller = replay(RadarTileStatus(loaded=2, has_echoes=False))
    controller._emit()
    assert controller._ui.state.data_status == 'Loaded tiles have no visible echoes'
    assert 'dry' not in controller._ui.state.data_status.lower()
    controller._radar_controller.frame_tile_status = RadarTileStatus()
    controller._emit()
    assert controller._ui.state.data_status == 'Waiting for map imagery…'


def test_partial_failure_is_not_masked_by_successful_tiles():
    controller = replay(RadarTileStatus(loaded=2, failed=1, has_echoes=True))
    controller._emit()
    assert controller._ui.state.data_status == 'Some map imagery unavailable'
    controller._radar_controller.frame_tile_status = RadarTileStatus(failed=1)
    controller._emit()
    assert controller._ui.state.data_status == 'Map imagery unavailable'


def test_old_history_selection_does_not_make_fresh_source_stale():
    controller = replay(RadarTileStatus(loaded=1, has_echoes=True))
    controller._radar_controller.frame_time = 1
    controller._emit()
    assert controller._ui.state.data_status == 'Imagery loaded'
    controller._clock = lambda: 4000
    controller._emit()
    assert 'over 30 minutes old' in controller._ui.state.data_status


def test_expired_forecast_is_labelled_separately_from_observed_radar():
    controller = replay(RadarTileStatus(loaded=1, has_echoes=True), forecast=True)
    controller._emit()
    assert controller._ui.state.data_status.startswith('Forecast period has ended')


def test_refresh_and_loading_states_are_distinct_and_failure_is_preserved():
    controller = replay(RadarTileStatus(pending=1))
    controller._emit()
    assert controller._ui.state.data_status == 'Loading map imagery…'
    controller._refreshing = True
    controller._emit()
    assert controller._ui.state.data_status == 'Refreshing radar data…'
    controller._refreshing = False
    controller._radar_load_failed('offline')
    assert controller._ui.state.data_status == 'Radar unavailable'
    assert controller._ui.state.status == 'Radar unavailable: offline'


def test_hidden_and_closed_health_callbacks_cannot_update_or_reschedule():
    controller = replay()
    controller.request_navigation_visible(True)
    old = controller._host.schedule_ui_callback.call_args.args[1]
    controller.request_navigation_visible(False)
    controller._ui.set_radar_state = Mock()
    before = controller._host.schedule_ui_callback.call_count
    old()
    controller._ui.set_radar_state.assert_not_called()
    assert controller._host.schedule_ui_callback.call_count == before
    controller.close()
    old()
    controller._ui.set_radar_state.assert_not_called()
