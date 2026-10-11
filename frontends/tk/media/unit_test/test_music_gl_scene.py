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
