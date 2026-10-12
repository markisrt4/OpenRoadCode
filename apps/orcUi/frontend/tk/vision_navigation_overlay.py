# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Format SI overlay values and draw a compact, fixed video HUD."""

from dataclasses import dataclass
from collections.abc import Callable
import tkinter as tk
from common.units import UnitSystem

from ui.navigation.route_types import RouteTurn
from ui.vision.navigation_overlay import NavigationOverlayState, OverlayGpsStatus

_ARROWS = {
    RouteTurn.UNKNOWN: "◇", RouteTurn.STRAIGHT: "↑", RouteTurn.LEFT: "↰",
    RouteTurn.RIGHT: "↱", RouteTurn.U_TURN: "↶", RouteTurn.ROUNDABOUT: "↻",
    RouteTurn.ARRIVE: "⚑",
}


@dataclass(frozen=True, slots=True)
class NavigationOverlayText:
    arrow: str
    headline: str
    road: str
    status: str


def overlay_text(state: NavigationOverlayState,
                 unit_system: UnitSystem = UnitSystem.IMPERIAL) -> NavigationOverlayText:
    """Own display units and prioritize degraded video/GPS and route conditions."""
    gps = {
        OverlayGpsStatus.NO_FIX: "NO GPS FIX", OverlayGpsStatus.LIVE: "GPS LIVE",
        OverlayGpsStatus.WEAK: "GPS WEAK", OverlayGpsStatus.CACHED: "GPS CACHED",
        OverlayGpsStatus.STALE: "GPS STALE",
    }[state.gps_status]
    metric = unit_system == UnitSystem.METRIC
    speed_unit = "km/h" if metric else "mph"
    factor = 3.6 if metric else 2.236936
    speed = f"— {speed_unit}" if state.speed_m_s is None else f"{state.speed_m_s * factor:.0f} {speed_unit}"
    status = f"{speed}  ·  {gps}"
    if state.video_stale:
        return NavigationOverlayText("!", "Video delayed — waiting for live frames", "", "VIDEO STALE")
    if state.complete:
        return NavigationOverlayText("⚑", "Destination reached", "", status)
    if state.gps_status not in (OverlayGpsStatus.LIVE, OverlayGpsStatus.WEAK):
        return NavigationOverlayText("◇", "Waiting for live GPS", "", status)
    if state.guidance_stale:
        return NavigationOverlayText("!", "Waiting for updated guidance", "", status)
    if state.off_route:
        return NavigationOverlayText("!", "Off route — check Navigation", "", status)
    if not state.instruction:
        return NavigationOverlayText("◇", "No active route", "", status)
    distance = ""
    if state.distance_m is not None:
        if metric:
            distance = (f"{state.distance_m / 1000:.1f} km" if state.distance_m >= 1000
                        else f"{state.distance_m:.0f} m")
        else:
            distance = (f"{state.distance_m / 1609.344:.1f} mi" if state.distance_m >= 1609.344
                        else f"{round(state.distance_m * 3.28084 / 10) * 10:.0f} ft")
    headline = f"{distance}  ·  {state.instruction}" if distance else state.instruction
    return NavigationOverlayText(_ARROWS[state.turn], headline, state.road_name or "", status)


def fit_lines(text: str, width: int, measure: Callable[[str], int], lines: int = 2) -> str:
    """Bound long instructions/roads to the HUD without covering other rows."""
    remaining = " ".join(text.split())
    fitted = []
    for index in range(lines):
        if measure(remaining) <= width:
            fitted.append(remaining)
            break
        final = index == lines - 1
        low, high = 0, len(remaining)
        while low < high:
            middle = (low + high + 1) // 2
            if measure(remaining[:middle] + ("…" if final else "")) <= width:
                low = middle
            else:
                high = middle - 1
        split = remaining.rfind(" ", 0, low + 1)
        count = split if split > 0 else low
        fitted.append(remaining[:count].rstrip() + ("…" if final else ""))
        remaining = remaining[count:].lstrip()
    return "\n".join(fitted)


def draw_navigation_overlay(canvas: tk.Canvas, state: NavigationOverlayState, *,
                            x: int, y: int, width: int,
                            height: int = 108,
                            unit_system: UnitSystem = UnitSystem.IMPERIAL) -> None:
    """Draw inside the video rectangle, keeping the center of the road clear."""
    canvas.delete("navigation-overlay")
    if not state.enabled or width < 180 or height < 108:
        return
    text = overlay_text(state, unit_system)
    tags = ("navigation-overlay",)
    panel_width = min(width - 16, 540)
    left, top = x + 8, y + 8
    warning = (state.video_stale or state.guidance_stale or state.off_route or
               state.gps_status != OverlayGpsStatus.LIVE)
    accent = "#ffc46b" if warning else "#46baff"
    measure = lambda text: int(canvas.tk.call("font", "measure", ("Sans", 11, "bold"), text))
    canvas.create_rectangle(left, top, left + panel_width, top + 92,
                            fill="#101b26", outline=accent, width=2, tags=tags)
    canvas.create_text(left + 24, top + 31, text=text.arrow, anchor=tk.CENTER,
                       fill=accent, font=("Sans", 25, "bold"), tags=tags)
    canvas.create_text(left + 50, top + 10,
                       text=fit_lines(text.headline, panel_width - 60, measure), anchor=tk.NW,
                       fill="#ffffff",
                       font=("Sans", 11, "bold"), tags=tags)
    if text.road:
        canvas.create_text(left + 50, top + 49,
                           text=fit_lines(text.road, panel_width - 60, measure, 1), anchor=tk.NW,
                           fill="#b8d8ea", font=("Sans", 9), tags=tags)
    canvas.create_text(left + 10, top + 72, text=text.status, anchor=tk.NW,
                       fill="#c4d0da", font=("Sans", 9, "bold"), tags=tags)
