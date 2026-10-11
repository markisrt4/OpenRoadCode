# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Presentation choices and camera fitting are independent of audio transport."""
from frontends.tk.media.music_gl_scene import MODE_LABELS, drum_camera_distance
from ui.music_visualizer import MusicVisualizationMode


def test_every_semantic_native_mode_is_selectable():
    assert set(MODE_LABELS) == set(MusicVisualizationMode)
    assert len(set(MODE_LABELS.values())) == len(MODE_LABELS)


def test_drum_zoom_moves_closer_and_narrow_windows_keep_kit_in_frame():
    assert drum_camera_distance(1.6, 1.6) < drum_camera_distance(1, 1.6)
    assert drum_camera_distance(2.8, .6) > drum_camera_distance(2.8, 1.6)


def test_drum_response_rejects_sustained_activity_and_keeps_real_hits():
    from frontends.tk.media.music_gl_scene import drum_activity
    from ui.music_visualizer.music_visualizer_types import MusicVisualizerOptions
    gain = MusicVisualizerOptions().drum_gain
    assert drum_activity(.2, gain) == 0
    assert drum_activity(.44, gain) < .1
    assert .4 < drum_activity(1, gain) < .7
    assert drum_activity(.8, .4) < drum_activity(.8, .8)


def test_detailed_geometry_is_cached_and_released():
    from unittest.mock import Mock
    from frontends.tk.media.music_gl_scene import NativeSceneGeometry
    gl, build = Mock(), Mock()
    gl.glGenLists.return_value = 42
    geometry = NativeSceneGeometry(gl)
    geometry.draw(('cymbal', .95), build)
    geometry.draw(('cymbal', .95), build)
    build.assert_called_once()
    gl.glGenLists.assert_called_once_with(1)
    assert gl.glCallList.call_count == 2
    geometry.close()
    geometry.close()
    gl.glDeleteLists.assert_called_once_with(42, 1)
