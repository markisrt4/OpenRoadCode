# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Richer orbital surfaces are cached and road activity reaches the center."""
from unittest.mock import Mock

from frontends.tk.media.music_gl_scene import NativeSceneGeometry
from frontends.tk.media.music_space_scenes import orbital_system, electric_freeway


def test_planet_surfaces_are_cached_per_context_and_include_moons_and_rings():
    gl, glu = Mock(), Mock()
    gl.glGenLists.side_effect = range(1, 6)
    geometry = NativeSceneGeometry(gl)
    orbital_system(gl, glu, None, (.4,)*24, .5, 2, geometry=geometry)
    orbital_system(gl, glu, None, (.6,)*24, .8, 3, geometry=geometry)
    assert gl.glGenLists.call_count == 5
    assert gl.glNormal3f.call_count > 1000
    assert glu.gluDisk.call_count == 4
    assert glu.gluSphere.call_count >= 12
    geometry.close()
    assert gl.glDeleteLists.call_count == 5


def test_freeway_has_center_tiles_and_cross_road_spectrum_gates():
    gl = Mock()
    electric_freeway(gl, (.5,)*24, .8, 2)
    vertices = [call.args for call in gl.glVertex3f.call_args_list]
    assert any(abs(x) < .5 and y > 0 for x, y, _z in vertices)
    assert any(abs(x) < .5 and y > 1 for x, y, _z in vertices)
    assert any(x == -2.2 and y > 2 for x, y, _z in vertices)
    assert gl.glBegin.call_count <= 4
