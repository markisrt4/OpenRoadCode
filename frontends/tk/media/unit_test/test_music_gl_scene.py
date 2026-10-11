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


def test_snare_and_both_kicks_have_clear_horizontal_gaps():
    from frontends.tk.media.music_gl_scene import (
        DOUBLE_KICK_X, KICK_RADIUS, SNARE_RADIUS, SNARE_X,
    )
    assert DOUBLE_KICK_X[1] - DOUBLE_KICK_X[0] > 2 * KICK_RADIUS * 1.025
    for x in (*DOUBLE_KICK_X, 0):
        assert abs(x - SNARE_X) > (KICK_RADIUS + SNARE_RADIUS) * 1.025


def test_drum_flash_retriggers_on_new_attack_not_sustained_sound():
    from types import SimpleNamespace
    from unittest.mock import patch
    from frontends.tk.media.native_music_visualizer import NativeMusicVisualizerPanel
    from ui.music_visualizer import VisualizerFrame
    panel = SimpleNamespace(_closed=False, _frame=VisualizerFrame(0, 0, 0, 0, ()),
                            _hits={}, _pulse=0)
    loud = VisualizerFrame(0, 0, 0, 0, (), kick=1, cymbal=.8)
    with patch('frontends.tk.media.native_music_visualizer.time.monotonic', return_value=1):
        NativeMusicVisualizerPanel.set_analysis_frame(panel, loud)
    with patch('frontends.tk.media.native_music_visualizer.time.monotonic', return_value=2):
        NativeMusicVisualizerPanel.set_analysis_frame(panel, loud)
    assert panel._hits['kick'] == (1, 1)
    assert panel._hits['cymbal'] == (.8, 1)
    NativeMusicVisualizerPanel.set_analysis_frame(panel, VisualizerFrame(0, 0, 0, 0, ()))
    with patch('frontends.tk.media.native_music_visualizer.time.monotonic', return_value=3):
        NativeMusicVisualizerPanel.set_analysis_frame(panel, loud)
    assert panel._hits['kick'] == (1, 3)
