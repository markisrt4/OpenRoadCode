# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Verify slider-crank geometry without a display or OpenGL dependencies."""

import math

import pytest

from apps.orcUi.frontend.tk.ecu_engine_gl import create_engine_gl, piston_position


@pytest.mark.parametrize('phase', [0, 0.125, 0.25, 0.5, 0.75, 1, 1.5])
def test_rods_keep_constant_length_and_pistons_stay_in_bore(phase):
    for cylinder in range(4):
        y, pin_y, pin_z = piston_position(phase, cylinder)
        assert math.hypot(y - pin_y, pin_z) == pytest.approx(0.78)
        assert 0.56 <= y <= 1.0
    assert piston_position(phase, 0) == piston_position(phase, 3)
    assert piston_position(phase, 1) == piston_position(phase, 2)


def test_pistons_have_opposing_top_and_bottom_dead_centers():
    assert piston_position(0, 0)[0] == pytest.approx(1.0)
    assert piston_position(0, 1)[0] == pytest.approx(0.56)
    assert piston_position(0.5, 0)[0] == pytest.approx(0.56)


def test_forced_canvas_does_not_require_gl_or_tk(monkeypatch):
    monkeypatch.setenv('OPENROAD_ECU_RENDERER', 'canvas')
    assert create_engine_gl(None, theme=None, on_failure=None) is None


def test_missing_backend_falls_back_without_creating_widgets(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def without_gl(name, *args, **kwargs):
        if name == "pyopengltk":
            raise ImportError("optional dependency not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.delenv("OPENROAD_ECU_RENDERER", raising=False)
    monkeypatch.setattr(builtins, "__import__", without_gl)
    assert create_engine_gl(None, theme=None, on_failure=None) is None


def test_flow_follows_distance_through_pipe_elbow():
    from apps.orcUi.frontend.tk.ecu_engine_gl import point_on_path

    path = ((0, 0, 0), (3, 0, 0), (3, 1, 0))
    assert point_on_path(path, 0.5) == pytest.approx((2, 0, 0))
    assert point_on_path(path, 0.875) == pytest.approx((3, 0.5, 0))
    assert point_on_path(path, 1) == path[-1]
