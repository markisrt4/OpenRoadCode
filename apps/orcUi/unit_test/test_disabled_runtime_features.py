"""Regression coverage for disabled runtime capabilities."""

from unittest.mock import Mock

import pytest

from apps.orcUi.cesium_map_runtime import CesiumMapRuntime
from apps.orcUi.composition.music_visualizer import (
    create_music_visualizer_session,
    selected_music_visualizer_source,
    selected_native_visualizer_source,
)
from ui.music_visualizer import MusicVisualizerSource
from ui.navigation.map_platform_if import MapPlatform


def test_disabled_cesium_rejects_platform_selection(monkeypatch):
    monkeypatch.setenv("ORC_NO_OPENGL", "1")
    native, viewer = Mock(), Mock()
    runtime = CesiumMapRuntime(native, viewer)
    try:
        runtime.launch(123)
        runtime.request_platform(MapPlatform.CESIUM)
        assert runtime.state.available_platforms == (MapPlatform.MAPLIBRE,)
        assert runtime.state.requested is MapPlatform.MAPLIBRE
        assert not runtime.state.busy
        assert runtime.state.status == "3D map intentionally disabled"
        viewer.open.assert_not_called()
        viewer.resume.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "source", [MusicVisualizerSource.PIPEWIRE, MusicVisualizerSource.ANDROID_PLAYBACK]
)
def test_disabled_audio_rejects_explicit_capture(monkeypatch, source):
    monkeypatch.setenv("ORC_NO_AUDIO", "1")
    monkeypatch.setenv("OPENROAD_MUSIC_VISUALIZER_SOURCE", source.value)
    assert selected_music_visualizer_source() is MusicVisualizerSource.SIMULATED
    assert selected_native_visualizer_source() is MusicVisualizerSource.SIMULATED
    assert create_music_visualizer_session(Mock(), source=source) is None
