# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Verify camera help coverage and lifecycle at the frontend boundary."""

from unittest.mock import Mock, patch, call
import pytest

from apps.orcUi.frontend.tk.navigation_panel import NavigationPanel
from apps.orcUi.frontend.tk.navigation_panel_layout import build_navigation_panel
from apps.orcUi.frontend.tk.navigation_screen import NavigationScreen


def test_right_side_controls_have_action_descriptions():
    panel = Mock()
    with patch("apps.orcUi.frontend.tk.navigation_panel_layout.tk"):
        build_navigation_panel(panel)
    descriptions = [call.args[1] for call in panel._add_tooltip.call_args_list]
    assert len(descriptions) == 13
    for text in ("Toggle following the vehicle", "Zoom in", "Zoom out",
                 "Current map zoom level", "Switch between overhead 2D and tilted 3D view",
                 "Rotate north to the top (turns follow off)",
                 "Center on the vehicle and resume following"):
        assert text in descriptions
    for direction in ("up", "down", "left", "right"):
        assert f"Pan the map {direction} on screen (turns follow off)" in descriptions
    assert any("Increase map tilt" in text for text in descriptions)
    assert any("Decrease map tilt" in text for text in descriptions)


def test_panel_cleanup_closes_all_tooltip_sessions_once():
    panel = object.__new__(NavigationPanel)
    first, second = Mock(), Mock()
    panel._tooltips = [first, second]
    panel.close_tooltips()
    panel.close_tooltips()
    first.close.assert_called_once()
    second.close.assert_called_once()
    assert panel._tooltips == []


def test_theme_rebuild_closes_tooltips_before_destroying_controls():
    panel = object.__new__(NavigationPanel)
    lifecycle = Mock()
    panel._tooltips = [lifecycle.tooltip]
    panel.close_radar_menu = Mock()
    panel.configure = Mock()
    panel.winfo_children = Mock(return_value=[lifecycle.control])
    panel._build = Mock()
    panel.set_theme_bundle(Mock())
    assert lifecycle.mock_calls == [
        call.tooltip.close(), call.control.destroy(),
    ]


@pytest.mark.parametrize("method", ["hide", "close"])
def test_navigation_screen_closes_tooltips_when_unmounted(method):
    screen = object.__new__(NavigationScreen)
    panel = Mock()
    screen._panel = panel
    screen._radar_handler = None
    screen._route_weather = None
    screen._close_places_session = Mock()
    screen._map_runtime = Mock()
    getattr(screen, method)()
    panel.close_tooltips.assert_called_once()
    assert screen._panel is None


def test_camera_controls_start_as_compact_collapsible_drawer():
    frames = []

    def frame(*args, **kwargs):
        widget = Mock()
        frames.append((widget, args, kwargs))
        return widget

    label = Mock()
    label.return_value.winfo_reqheight.return_value = 18
    with patch.multiple("apps.orcUi.frontend.tk.navigation_panel_layout.tk",
                        Frame=frame, Button=Mock(), Label=label,
                        Menubutton=Mock(), Menu=Mock(), PhotoImage=Mock(), Toplevel=Mock()):
        build_navigation_panel(Mock())
    controls = next(widget for widget, _args, kwargs in frames if kwargs.get("width") == 54)
    rail = next(widget for widget, args, _kwargs in frames if args and args[0] is controls)
    assert controls.grid_propagate.call_args.args == (False,)
    assert not rail.place.called
