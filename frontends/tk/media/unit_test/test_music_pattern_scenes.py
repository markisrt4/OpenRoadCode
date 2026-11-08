# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""New scene shapes stay distinct and dense without excessive GL draw blocks."""
from unittest.mock import Mock

from frontends.tk.media.music_pattern_scenes import explosion_field, star_dance, kaleidoscope


def test_sparks_and_stars_use_distinct_geometry():
    sparks, stars = Mock(), Mock()
    explosion_field(sparks, .5, 2)
    star_dance(stars, (.4,)*24, .5, 2, 1.5)
    assert sparks.glVertex3f.call_count > 500
    assert sparks.glBegin.call_args_list[0].args == (sparks.GL_LINES,)
    assert stars.glVertex2f.call_count > 500
    assert any(call.args == (stars.GL_TRIANGLES,) for call in stars.glBegin.call_args_list)
    assert stars.glBegin.call_count <= 3


def test_dense_mirrored_facets_fill_both_axes_and_change_with_audio():
    quiet, loud = Mock(), Mock()
    kaleidoscope(quiet, (0,)*24, 0, 2, 1.5)
    kaleidoscope(loud, (1,)*24, 1, 2, 1.5)
    points = [call.args for call in loud.glVertex2f.call_args_list]
    assert len(points) >= 2000
    assert min(x for x, _ in points) < -1.5
    assert max(x for x, _ in points) > 1.5
    assert min(y for _, y in points) < -1
    assert max(y for _, y in points) > 1
    assert quiet.glVertex2f.call_args_list != loud.glVertex2f.call_args_list
    assert quiet.glColor3f.call_args_list != loud.glColor3f.call_args_list
    loud.glBegin.assert_called_once_with(loud.GL_TRIANGLES)
