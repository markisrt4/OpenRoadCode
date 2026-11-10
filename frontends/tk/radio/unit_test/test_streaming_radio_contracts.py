# SPDX-License-Identifier: MIT

"""Test presentation contract consumption without creating a Tk root."""

from dataclasses import replace
from io import BytesIO
from unittest.mock import Mock

from PIL import Image

from frontends.tk.radio.streaming_radio_panel import StreamingRadioPanel
from frontends.tk.radio.streaming_radio_now_playing import StreamingRadioNowPlaying
from ui.radio.streaming_radio_state import StreamingRadioBrowserState, StreamingRadioPlaybackState
from ui.radio.streaming_radio_types import StreamingRadioStation


STATION = StreamingRadioStation("one", "One", "https://radio.test/one",
                                artwork_url="https://radio.test/logo")


def view():
    panel = object.__new__(StreamingRadioPanel)
    panel._request_handler = Mock()
    panel._session = Mock()
    panel._active = True
    panel._destroyed = False
    panel._selected_station = None
    panel._playback = StreamingRadioPlaybackState()
    panel._on_station_selected = None
    panel._selection_label = Mock()
    panel._paint_filters = Mock()
    panel._paint_playback_status = Mock()
    panel._render_stations = Mock()
    panel._show_status = Mock()
    panel._artwork_urls = {}
    panel._artwork_images = {}
    panel._artwork_labels = {}
    return panel


def test_widget_emits_semantic_requests_only():
    panel = view()
    handler = panel._request_handler
    panel._request_play(STATION)
    handler.request_play.assert_called_once_with("one")
    panel._request_stop()
    handler.request_stop.assert_called_once()
    panel._toggle_station_favorite(STATION)
    handler.request_toggle_favorite.assert_called_once_with("one")
    panel.set_streaming_request_handler(None)
    panel._request_stop()
    handler.request_stop.assert_called_once()


def test_widget_renders_snapshot_and_invalidates_artwork_when_url_changes():
    panel = view()
    panel._artwork_urls["one"] = "https://radio.test/old-logo"
    panel._artwork_images["one"] = Mock()
    state = StreamingRadioBrowserState(
        stations=(STATION,), favorite_station_ids=frozenset(("one",)),
        playback=StreamingRadioPlaybackState(STATION, True), playback_busy=True,
    )
    panel.set_streaming_state(state)
    assert panel._playback is state.playback and panel._playback_busy
    assert panel.favorite_station_ids == frozenset(("one",))
    assert "one" not in panel._artwork_images
    panel._render_stations.assert_called_once()


def test_loading_and_error_state_do_not_render_old_station_cards():
    panel = view()
    panel.set_streaming_state(StreamingRadioBrowserState(loading=True))
    panel._show_status.assert_called_with("Loading local stations…")
    panel._render_stations.assert_not_called()
    panel.set_streaming_state(StreamingRadioBrowserState(message="directory failed", error=True))
    panel._show_status.assert_called_with("directory failed", danger=True)


def test_artwork_delivery_updates_current_label_and_ignores_inactive_view(monkeypatch):
    panel = view()
    label = Mock()
    panel._artwork_labels["one"] = label
    payload = BytesIO()
    Image.new("RGB", (3, 3), "green").save(payload, format="PNG")
    image = Mock()
    photo = Mock(return_value=image)
    monkeypatch.setattr("frontends.tk.radio.streaming_radio_panel.ImageTk.PhotoImage", photo)
    panel.set_station_artwork("one", payload.getvalue())
    assert panel._artwork_images["one"] is image
    label.configure.assert_called_once()
    panel.deactivate()
    panel.set_station_artwork("one", payload.getvalue())
    photo.assert_called_once()
    panel._session.deactivate.assert_called_once()


def test_corrupt_artwork_retains_placeholder():
    panel = view()
    panel.set_station_artwork("one", b"not an image")
    assert panel._artwork_images == {}


def test_destroy_retires_session_once_even_when_toolkit_cleanup_is_repeated(monkeypatch):
    panel = view()
    destroy = Mock()
    monkeypatch.setattr("tkinter.Frame.destroy", destroy)
    panel.destroy()
    panel.destroy()
    panel._session.close.assert_called_once()
    destroy.assert_called_once()


def test_home_summary_reads_one_immutable_snapshot_per_refresh():
    panel = object.__new__(StreamingRadioNowPlaying)
    panel._state_source = Mock()
    panel._state_source.snapshot.return_value = StreamingRadioPlaybackState(STATION, True)
    panel._online_allowed = lambda: False
    panel._ui = Mock()
    panel._stream_button = Mock()
    panel._status, panel._station, panel._detail = Mock(), Mock(), Mock()
    panel.winfo_exists = Mock(return_value=True)
    panel.after = Mock(return_value="refresh")
    panel._refresh()
    panel._state_source.snapshot.assert_called_once()
    panel._station.configure.assert_called_once_with(text="One")
    assert panel._after_id == "refresh"
