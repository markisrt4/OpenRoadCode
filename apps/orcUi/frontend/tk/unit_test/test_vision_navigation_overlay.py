# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Readable, safe fallback text and frontend-owned display conversions."""

from unittest.mock import Mock
from common.units import UnitSystem
from apps.orcUi.frontend.tk.vision_navigation_overlay import overlay_text, draw_navigation_overlay, fit_lines
from ui.navigation.route_types import RouteTurn
from ui.vision.navigation_overlay import NavigationOverlayState, OverlayGpsStatus


def test_si_guidance_formats_in_the_selected_units():
    state = NavigationOverlayState(
        instruction="Turn left", turn=RouteTurn.LEFT, road_name="Main Street",
        distance_m=100, speed_m_s=10, gps_status=OverlayGpsStatus.LIVE,
    )
    imperial = overlay_text(state)
    metric = overlay_text(state, UnitSystem.METRIC)
    assert imperial.arrow == "↰" and imperial.road == "Main Street"
    assert imperial.headline == "330 ft  ·  Turn left"
    assert "22 mph" in imperial.status
    assert metric.headline == "100 m  ·  Turn left"
    assert "36 km/h" in metric.status


def test_stale_gps_suppresses_the_old_actionable_instruction():
    state = NavigationOverlayState(instruction="Turn right now", turn=RouteTurn.RIGHT,
                                   distance_m=1, gps_status=OverlayGpsStatus.STALE)
    text = overlay_text(state)
    assert text.headline == "Waiting for live GPS"
    assert "GPS STALE" in text.status
    assert text.arrow == "◇"


def test_hidden_overlay_only_removes_its_own_canvas_items():
    canvas = Mock()
    draw_navigation_overlay(canvas, NavigationOverlayState(enabled=False), x=0, y=0, width=500)
    canvas.delete.assert_called_once_with("navigation-overlay")
    canvas.create_rectangle.assert_not_called()
    canvas.create_image.assert_not_called()


def test_arrival_and_off_route_use_clear_labels():
    assert overlay_text(NavigationOverlayState(complete=True)).headline == "Destination reached"
    state = NavigationOverlayState(off_route=True, gps_status=OverlayGpsStatus.LIVE)
    assert overlay_text(state).headline == "Off route — check Navigation"


def test_long_instructions_fit_two_rows_with_ellipsis_and_full_turn_prefix():
    rendered = fit_lines("Turn left onto A Very Long Road Name In This Village", 140,
                         lambda text: len(text) * 7)
    lines = rendered.splitlines()
    assert len(lines) == 2 and lines[0].startswith("Turn left")
    assert lines[-1].endswith("…")
    assert all(len(line) * 7 <= 140 for line in lines)
