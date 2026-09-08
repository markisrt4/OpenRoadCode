# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Reusable Tk dashboard panel for off-road navigation data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
import math
import tkinter as tk

from ui.navigation import (
    GroundTrackUiIf,
    HeadingReference,
    NavigationRequestHandlerIf,
    OrientationUiIf,
    PositionFix,
    PositionUiIf,
    SatelliteInfo,
    TranslationUiIf,
)
from frontends.tk.automotive.offroad_theme import OffroadTheme
from ui.system import StatusMessage, StatusSeverity, StatusUiIf, StatusValue
from ui.theme import StyleSheet


# ORC automotive palette.
BACKGROUND = "#05090d"
PANEL = "#0b1117"
GRID = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
BLUE = "#168bd1"
GREEN = "#84ce1f"
AMBER = "#d6ad22"
RED = "#f15a16"
SKY = "#18344b"
GROUND = "#493825"


@dataclass(slots=True)
class _Vector:
    x: float | None = None
    y: float | None = None
    z: float | None = None


@dataclass(slots=True)
class _GpsDisplayState:
    altitude_m: float | None = None
    speed_mps: float | None = None
    course_deg: float | None = None
    satellites_used: int | None = None


@dataclass(slots=True)
class _DashboardState:
    heading_deg: float = 0.0
    heading_reference: HeadingReference = HeadingReference.RELATIVE
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    linear_acceleration_mps2: _Vector = field(default_factory=_Vector)
    gps: _GpsDisplayState = field(default_factory=_GpsDisplayState)


def _normalize_heading(heading_deg: float) -> float:
    return heading_deg % 360.0


def _cardinal_direction(heading_deg: float) -> str:
    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    index = int((_normalize_heading(heading_deg) + 22.5) // 45.0) % 8
    return directions[index]


def _tilt_severity(
    pitch_deg: float,
    roll_deg: float,
    pitch_warning_deg: float,
    roll_warning_deg: float,
) -> str:
    pitch_ratio = abs(pitch_deg) / pitch_warning_deg
    roll_ratio = abs(roll_deg) / roll_warning_deg
    ratio = max(pitch_ratio, roll_ratio)
    if ratio >= 1.0:
        return "warning"
    if ratio >= 0.75:
        return "caution"
    return "normal"


def _is_capsized(pitch_deg: float, roll_deg: float) -> bool:
    """Return whether attitude indicates the vehicle is substantially inverted."""

    return abs(roll_deg) >= 120.0 or abs(pitch_deg) >= 120.0


def _rotate_screen_point(
    point: tuple[float, float],
    center_x: float,
    center_y: float,
    angle_deg: float,
) -> tuple[float, float]:
    """Rotate a local screen point clockwise around a screen center."""

    x, y = point
    angle = math.radians(angle_deg)
    return (
        center_x + x * math.cos(angle) - y * math.sin(angle),
        center_y + x * math.sin(angle) + y * math.cos(angle),
    )


class OffroadDashboardPanel(
    tk.Frame,
    OrientationUiIf,
    TranslationUiIf,
    PositionUiIf,
    GroundTrackUiIf,
    StatusUiIf,
):
    """Display trail-oriented navigation data through narrow UI contracts."""

    def __init__(
        self,
        parent: tk.Misc,
        pitch_warning_deg: float,
        roll_warning_deg: float,
        request_handler: NavigationRequestHandlerIf | None = None,
        theme: OffroadTheme | None = None,
    ) -> None:
        self._theme = theme or OffroadTheme(
            background=BACKGROUND,
            panel=PANEL,
            border=GRID,
            text=TEXT,
            muted=MUTED,
            primary=BLUE,
            success=GREEN,
            warning=AMBER,
            danger=RED,
            sky=SKY,
            ground=GROUND,
            control_background="#101820",
            control_active=BLUE,
            control_text=TEXT,
        )
        super().__init__(parent, bg=self._theme.background)
        self._pitch_warning_deg = pitch_warning_deg
        self._roll_warning_deg = roll_warning_deg
        self._request_handler = request_handler
        self._state = _DashboardState()
        self._has_orientation = False
        self._position: PositionFix | None = None
        self._redraw_pending = False

        self._canvas = tk.Canvas(
            self,
            bg=self._theme.background,
            highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", lambda _event: self._draw())

        controls = tk.Frame(self, bg=self._theme.panel)
        self._controls = controls
        controls.pack(fill=tk.X)
        self._button(
            controls, "CALIBRATE", self._request_calibration
        ).pack(side=tk.LEFT, padx=(10, 4), pady=7)
        self._button(
            controls, "ZERO HEADING", self._request_heading_reset
        ).pack(side=tk.LEFT, padx=4, pady=7)

        self._status = tk.StringVar(value="STARTING")
        self._status_label = tk.Label(
            controls,
            textvariable=self._status,
            fg=self._theme.success,
            bg=self._theme.panel,
            font=("TkFixedFont", 10, "bold"),
        )
        self._status_label.pack(side=tk.RIGHT, padx=14)

    def set_theme(self, theme: OffroadTheme) -> None:
        """Apply a resolved off-road theme and redraw the dashboard."""

        self._theme = theme
        self.configure(bg=theme.background)
        self._canvas.configure(bg=theme.background)
        self._controls.configure(bg=theme.panel)
        self._status_label.configure(bg=theme.panel)
        for child in self._controls.winfo_children():
            if isinstance(child, tk.Button):
                child.configure(
                    bg=theme.control_background,
                    fg=theme.control_text,
                    activebackground=theme.control_active,
                    activeforeground=theme.control_text,
                )
        self._draw()

    def set_style_sheet(self, sheet: StyleSheet) -> None:
        """Apply the .automotive-offroad stylesheet rule."""

        self.set_theme(OffroadTheme.from_style_sheet(sheet))

    def set_navigation_request_handler(
        self,
        handler: NavigationRequestHandlerIf | None,
    ) -> None:
        """Connect or clear navigation-control requests.

        @param handler Request consumer, or None to disable the controls.
        """
        self._request_handler = handler

    def set_heading(
        self,
        heading_rad: float | None,
        reference: HeadingReference = HeadingReference.TRUE_NORTH,
    ) -> None:
        """Set displayed heading; the dashboard labels relative headings.

        @param heading_rad Heading in radians, or None when unavailable.
        @param reference Supplied north reference.
        """
        self._has_orientation = heading_rad is not None
        self._state.heading_reference = reference
        self._state.heading_deg = (
            math.degrees(heading_rad) if heading_rad is not None else 0.0
        )
        self._request_draw()

    def set_pitch(self, pitch_rad: float | None) -> None:
        """Set displayed pitch.

        @param pitch_rad Pitch in radians, or None.
        """
        self._state.pitch_deg = (
            math.degrees(pitch_rad) if pitch_rad is not None else 0.0
        )
        self._request_draw()

    def set_roll(self, roll_rad: float | None) -> None:
        """Set displayed roll.

        @param roll_rad Roll in radians, or None.
        """
        self._state.roll_deg = (
            math.degrees(roll_rad) if roll_rad is not None else 0.0
        )
        self._request_draw()

    def set_rate_of_climb(self, rate_mps: float | None) -> None:
        """Accept climb rate, which is not currently rendered.

        @param rate_mps Climb rate in metres per second, or None.
        """
        del rate_mps

    def set_accel_x(self, acceleration_x_mps2: float | None) -> None:
        """Set fore/aft linear acceleration.

        @param acceleration_x_mps2 Acceleration in metres per second squared.
        """
        self._state.linear_acceleration_mps2.x = acceleration_x_mps2
        self._request_draw()

    def set_accel_y(self, acceleration_y_mps2: float | None) -> None:
        """Set lateral linear acceleration.

        @param acceleration_y_mps2 Acceleration in metres per second squared.
        """
        self._state.linear_acceleration_mps2.y = acceleration_y_mps2
        self._request_draw()

    def set_accel_z(self, acceleration_z_mps2: float | None) -> None:
        """Store vertical linear acceleration.

        @param acceleration_z_mps2 Acceleration in metres per second squared.
        """
        self._state.linear_acceleration_mps2.z = acceleration_z_mps2

    def set_accel_total(self, acceleration_magnitude_mps2: float | None) -> None:
        """Accept total acceleration, which is not currently rendered.

        @param acceleration_magnitude_mps2 Acceleration magnitude, or None.
        """
        del acceleration_magnitude_mps2

    def set_position(self, position_fix: PositionFix | None) -> None:
        """Set position-derived altitude.

        @param position_fix Position fix, or None when unavailable.
        """
        self._position = position_fix
        self._state.gps.altitude_m = (
            position_fix.altitude_m if position_fix is not None else None
        )
        self._request_draw()

    def set_satellites(self, satellites: Sequence[SatelliteInfo]) -> None:
        """Set the count of satellites used in the current fix.

        @param satellites Complete satellite snapshot.
        """
        self._state.gps.satellites_used = sum(
            satellite.is_used_in_fix for satellite in satellites
        )
        self._request_draw()

    def set_ground_speed(self, speed_mps: float | None) -> None:
        """Set speed over ground.

        @param speed_mps Speed in metres per second, or None.
        """
        self._state.gps.speed_mps = speed_mps
        self._request_draw()

    def set_course_over_ground(self, course_rad: float | None) -> None:
        """Set actual direction of travel over the ground.

        @param course_rad Clockwise radians from true north, or None.
        """
        self._state.gps.course_deg = (
            math.degrees(course_rad) if course_rad is not None else None
        )
        self._request_draw()

    def set_status(self, status: StatusValue) -> None:
        """Set the concise dashboard status line.

        @param status Structured status, text, or None.
        """
        if isinstance(status, StatusMessage):
            text = status.summary
            color = {
                StatusSeverity.INFORMATION: self._theme.text,
                StatusSeverity.SUCCESS: self._theme.success,
                StatusSeverity.WARNING: self._theme.warning,
                StatusSeverity.ERROR: self._theme.danger,
            }[status.severity]
        else:
            text = status or ""
            color = self._theme.success
        self._status_label.configure(fg=color)
        self._status.set(text.upper())

    def _button(
        self,
        parent: tk.Widget,
        text: str,
        command: object,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=self._theme.control_background,
            fg=self._theme.control_text,
            activebackground=self._theme.control_active,
            activeforeground=self._theme.control_text,
            relief=tk.FLAT,
            padx=14,
            font=("TkDefaultFont", 9, "bold"),
        )

    def _draw(self) -> None:
        self._redraw_pending = False
        self._canvas.delete("all")
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        state = self._state if self._has_orientation else None

        self._draw_header(width, state)

        content_top = 88
        content_bottom = height - 106
        center_x = width / 2.0
        center_y = (content_top + content_bottom) / 2.0
        horizon_radius = min(width * 0.24, (content_bottom - content_top) * 0.48)

        pitch = state.pitch_deg if state is not None else 0.0
        roll = state.roll_deg if state is not None else 0.0
        self._draw_tilt_meter(
            center_x,
            center_y,
            horizon_radius,
            pitch,
            roll,
            state is not None,
        )
        if state is not None and _is_capsized(
            state.pitch_deg, state.roll_deg
        ):
            self._draw_capsized_banner(
                center_x,
                center_y,
                horizon_radius,
            )

        side_width = max(180.0, width * 0.2)
        self._draw_pitch_card(
            18,
            content_top + 18,
            side_width,
            pitch if state is not None else None,
            self._pitch_warning_deg,
        )
        self._draw_angle_card(
            width - side_width - 18,
            content_top + 18,
            side_width,
            "ROLL",
            roll if state is not None else None,
            "RIGHT" if roll >= 0 else "LEFT",
            self._roll_warning_deg,
        )
        heading_card_y = content_top + 174
        if heading_card_y + 164 <= content_bottom:
            self._draw_heading_card(
                width - side_width - 18,
                heading_card_y,
                side_width,
                state,
            )

        self._draw_bottom_cards(width, height, state)

    def _request_draw(self) -> None:
        if self._redraw_pending:
            return
        self._redraw_pending = True
        self.after_idle(self._draw)

    def _draw_capsized_banner(
        self,
        center_x: float,
        center_y: float,
        radius: float,
    ) -> None:
        """Draw a deliberately dramatic inverted-vehicle warning."""

        banner_y = center_y + radius * 0.55
        half_width = radius * 0.72
        self._canvas.create_rectangle(
            center_x - half_width,
            banner_y - 27,
            center_x + half_width,
            banner_y + 27,
            fill="#5b1512",
            outline=self._theme.danger,
            width=3,
        )
        self._canvas.create_text(
            center_x,
            banner_y - 8,
            text="CAPSIZED",
            fill="#ffffff",
            font=("TkDefaultFont", 18, "bold"),
        )
        self._canvas.create_text(
            center_x,
            banner_y + 13,
            text="Call the police? Maybe the winch crew first.",
            fill="#ffd6d2",
            font=("TkDefaultFont", 8, "bold"),
        )

    def _draw_header(
        self,
        width: int,
        state: _DashboardState | None,
    ) -> None:
        self._canvas.create_rectangle(0, 0, width, 82, fill=self._theme.panel, outline="")
        heading = state.heading_deg if state is not None else 0.0
        reference_text = (
            {
                HeadingReference.TRUE_NORTH: "TRUE",
                HeadingReference.MAGNETIC_NORTH: "MAG",
                HeadingReference.RELATIVE: "REL",
            }[state.heading_reference]
            if state is not None
            else "REL"
        )
        heading_text = (
            f"{heading:03.0f}°"
            if state is not None
            else "---°"
        )
        self._canvas.create_text(
            width / 2,
            22,
            text=heading_text,
            fill=self._theme.text,
            font=("TkFixedFont", 22, "bold"),
        )

        pixels_per_degree = max(3.0, width / 180.0)
        for offset in range(-60, 61, 5):
            marker_heading = _normalize_heading(heading + offset)
            x = width / 2 + offset * pixels_per_degree
            major = offset % 15 == 0
            y1 = 52
            y2 = 72 if major else 64
            self._canvas.create_line(x, y1, x, y2, fill=self._theme.border, width=2)
            if major:
                self._canvas.create_text(
                    x,
                    44,
                    text=f"{marker_heading:.0f}",
                    fill=self._theme.muted,
                    font=("TkFixedFont", 9),
                )
        self._canvas.create_polygon(
            width / 2 - 7,
            78,
            width / 2 + 7,
            78,
            width / 2,
            66,
            fill=self._theme.warning,
            outline="",
        )

    def _draw_heading_card(
        self,
        x: float,
        y: float,
        width: float,
        state: _DashboardState | None,
    ) -> None:
        """Draw relative heading and optional GPS course from above."""

        height = 164
        self._canvas.create_rectangle(
            x, y, x + width, y + height, fill=self._theme.panel, outline=self._theme.border, width=2
        )
        self._canvas.create_text(
            x + 14,
            y + 14,
            anchor=tk.NW,
            text="HEADING",
            fill=self._theme.muted,
            font=("TkDefaultFont", 10, "bold"),
        )

        center_x = x + width / 2
        center_y = y + 87
        radius = min(53.0, width * 0.29)
        self._canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            outline=self._theme.border,
            width=2,
        )
        self._canvas.create_line(
            center_x,
            center_y - radius + 3,
            center_x,
            center_y + radius - 3,
            fill="#1c322a",
        )
        self._canvas.create_line(
            center_x - radius + 3,
            center_y,
            center_x + radius - 3,
            center_y,
            fill="#1c322a",
        )
        self._canvas.create_text(
            center_x,
            center_y - radius - 9,
            text="0",
            fill=self._theme.success,
            font=("TkDefaultFont", 7, "bold"),
        )

        heading = state.heading_deg if state is not None else 0.0
        gps = state.gps if state is not None else None
        if gps is not None and gps.course_deg is not None:
            self._draw_direction_arrow(
                center_x,
                center_y,
                radius * 0.86,
                gps.course_deg,
                AMBER,
                3,
            )
            self._canvas.create_text(
                x + width - 10,
                y + 16,
                anchor=tk.NE,
                text=(
                    f"GPS {gps.course_deg:.0f}° "
                    f"{_cardinal_direction(gps.course_deg)}"
                ),
                fill=self._theme.warning,
                font=("TkDefaultFont", 8, "bold"),
            )

        # A compact top-view Jeep points along relative heading.
        local_body = (
            (-13, 25), (-17, 9), (-15, -21), (-8, -31),
            (8, -31), (15, -21), (17, 9), (13, 25),
        )
        local_cabin = ((-10, 8), (-10, -13), (10, -13), (10, 8))

        def transform(
            points: tuple[tuple[float, float], ...],
        ) -> tuple[float, ...]:
            transformed: list[float] = []
            for point in points:
                transformed.extend(
                    _rotate_screen_point(
                        point,
                        center_x,
                        center_y,
                        heading,
                    )
                )
            return tuple(transformed)

        self._canvas.create_polygon(
            *transform(local_body),
            fill="#274536",
            outline=self._theme.success if state is not None else MUTED,
            width=2,
            joinstyle=tk.ROUND,
        )
        self._canvas.create_polygon(
            *transform(local_cabin),
            fill="#102636",
            outline="#7ea3b8",
            width=1,
        )
        nose_x, nose_y = _rotate_screen_point(
            (0, -31),
            center_x,
            center_y,
            heading,
        )
        self._canvas.create_oval(
            nose_x - 3,
            nose_y - 3,
            nose_x + 3,
            nose_y + 3,
            fill=self._theme.success,
            outline="",
        )

        reference_text = (
            {
                HeadingReference.TRUE_NORTH: "TRUE",
                HeadingReference.MAGNETIC_NORTH: "MAG",
                HeadingReference.RELATIVE: "REL",
            }[state.heading_reference]
            if state is not None
            else "REL"
        )
        relative_text = (
            f"{reference_text} {heading:03.0f}°"
            if state is not None
            else "REL ---°"
        )
        self._canvas.create_text(
            center_x,
            y + height - 10,
            text=relative_text,
            fill=self._theme.text,
            font=("TkFixedFont", 9, "bold"),
        )

    def _draw_direction_arrow(
        self,
        center_x: float,
        center_y: float,
        length: float,
        direction_deg: float,
        color: str,
        width: int,
    ) -> None:
        tip_x, tip_y = _rotate_screen_point(
            (0, -length),
            center_x,
            center_y,
            direction_deg,
        )
        self._canvas.create_line(
            center_x,
            center_y,
            tip_x,
            tip_y,
            fill=color,
            width=width,
            arrow=tk.LAST,
            arrowshape=(10, 12, 5),
        )

    def _draw_pitch_card(
        self,
        x: float,
        y: float,
        width: float,
        value: float | None,
        warning_deg: float,
    ) -> None:
        """Draw pitch with a side-profile Jeep against a level reference."""

        height = 225
        self._canvas.create_rectangle(
            x, y, x + width, y + height, fill=self._theme.panel, outline=self._theme.border, width=2
        )
        self._canvas.create_text(
            x + 14,
            y + 16,
            anchor=tk.NW,
            text="PITCH",
            fill=self._theme.muted,
            font=("TkDefaultFont", 11, "bold"),
        )

        if value is None:
            display = "--.-°"
            color = MUTED
            pitch = 0.0
            direction = "--"
        else:
            display = f"{abs(value):.1f}°"
            ratio = abs(value) / warning_deg
            color = RED if ratio >= 1 else AMBER if ratio >= 0.75 else GREEN
            pitch = value
            direction = "NOSE UP" if value >= 0 else "NOSE DOWN"

        self._canvas.create_text(
            x + width / 2,
            y + 57,
            text=display,
            fill=color,
            font=("TkFixedFont", 27, "bold"),
        )

        center_x = x + width / 2
        center_y = y + 122
        half_level = width * 0.34
        self._canvas.create_line(
            center_x - half_level,
            center_y + 25,
            center_x + half_level,
            center_y + 25,
            fill=self._theme.warning,
            width=2,
            dash=(5, 4),
        )
        self._canvas.create_text(
            center_x + half_level,
            center_y + 36,
            anchor=tk.E,
            text="LEVEL",
            fill=self._theme.warning,
            font=("TkDefaultFont", 7, "bold"),
        )

        # Pitch is easier to read as an incline reference than as another
        # miniature vehicle. The center attitude gauge already owns the
        # vehicle graphic.
        incline_half = width * 0.27
        incline_angle = math.radians(-pitch)
        dx = incline_half * math.cos(incline_angle)
        dy = incline_half * math.sin(incline_angle)

        self._canvas.create_line(
            center_x - dx,
            center_y - dy,
            center_x + dx,
            center_y + dy,
            fill=color if value is not None else self._theme.muted,
            width=5,
        )
        self._canvas.create_oval(
            center_x - 5,
            center_y - 5,
            center_x + 5,
            center_y + 5,
            fill=self._theme.warning,
            outline="",
        )

        self._canvas.create_text(
            x + width - 12,
            y + 17,
            anchor=tk.NE,
            text=direction,
            fill=color if value is not None else MUTED,
            font=("TkDefaultFont", 9, "bold"),
        )

    def _draw_tilt_meter(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        pitch_deg: float,
        roll_deg: float,
        has_state: bool,
    ) -> None:
        self._canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill="#0a1512",
            outline=self._theme.border,
            width=3,
        )

        # A fixed terrain plane makes the vehicle's roll immediately legible.
        for offset, color, line_width in (
            (-48, "#193027", 1),
            (-24, "#27483a", 1),
            (0, AMBER, 3),
            (24, "#27483a", 1),
            (48, "#193027", 1),
        ):
            half_width = math.sqrt(
                max(0.0, (radius - 10) ** 2 - offset**2)
            )
            line_options: dict[str, object] = {
                "fill": color,
                "width": line_width,
            }
            if offset:
                line_options["dash"] = (5, 5)
            self._canvas.create_line(
                center_x - half_width,
                center_y + offset,
                center_x + half_width,
                center_y + offset,
                **line_options,
            )
        self._canvas.create_text(
            center_x + radius - 16,
            center_y - 10,
            anchor=tk.E,
            text="LEVEL",
            fill=self._theme.warning,
            font=("TkDefaultFont", 8, "bold"),
        )

        for angle in range(-60, 61, 15):
            marker_angle = math.radians(angle - 90)
            inner = radius - (16 if angle % 30 == 0 else 10)
            self._canvas.create_line(
                center_x + inner * math.cos(marker_angle),
                center_y + inner * math.sin(marker_angle),
                center_x + (radius - 3) * math.cos(marker_angle),
                center_y + (radius - 3) * math.sin(marker_angle),
                fill=self._theme.muted,
                width=2,
            )

        self._draw_front_jeep(center_x, center_y, radius, roll_deg)
        self._draw_pitch_scale(
            center_x,
            center_y,
            radius,
            pitch_deg,
        )

        severity = _tilt_severity(
            pitch_deg,
            roll_deg,
            self._pitch_warning_deg,
            self._roll_warning_deg,
        )
        severity_color = {
            "normal": GREEN,
            "caution": AMBER,
            "warning": RED,
        }[severity]
        label = severity.upper() if has_state else "NO DATA"
        self._canvas.create_text(
            center_x,
            center_y + radius - 16,
            text=label,
            fill=severity_color,
            font=("TkDefaultFont", 12, "bold"),
        )

    def _draw_front_jeep(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        roll_deg: float,
    ) -> None:
        """Draw a recognizable front-view Jeep rotated by vehicle roll."""

        scale = radius / 150.0

        def transform(
            points: tuple[tuple[float, float], ...],
        ) -> tuple[float, ...]:
            transformed: list[float] = []
            for x, y in points:
                screen_point = _rotate_screen_point(
                    (x * scale, y * scale),
                    center_x,
                    center_y,
                    roll_deg,
                )
                transformed.extend(screen_point)
            return tuple(transformed)

        body = (
            (-65, -5), (-55, -42), (-38, -54), (38, -54),
            (55, -42), (65, -5), (61, 40), (-61, 40),
        )
        windshield = ((-34, -47), (34, -47), (43, -14), (-43, -14))
        left_tire = ((-73, 8), (-57, 8), (-55, 48), (-72, 48))
        right_tire = ((57, 8), (73, 8), (72, 48), (55, 48))

        self._canvas.create_polygon(
            *transform(left_tire),
            fill="#111613",
            outline="#80958a",
            width=2,
        )
        self._canvas.create_polygon(
            *transform(right_tire),
            fill="#111613",
            outline="#80958a",
            width=2,
        )
        self._canvas.create_polygon(
            *transform(body),
            fill="#263d31",
            outline=TEXT,
            width=3,
            joinstyle=tk.ROUND,
        )
        self._canvas.create_polygon(
            *transform(windshield),
            fill="#102636",
            outline="#7ea3b8",
            width=2,
        )

        # Seven-slot grille.
        for grille_x in (-27, -18, -9, 0, 9, 18, 27):
            self._canvas.create_line(
                *transform(((grille_x, 7), (grille_x, 31))),
                fill="#9bad9f",
                width=max(1, int(2 * scale)),
            )

        # Round headlights retain their shape while their centers follow roll.
        for headlight_x in (-43, 43):
            x, y = _rotate_screen_point(
                (headlight_x * scale, 16 * scale),
                center_x,
                center_y,
                roll_deg,
            )
            lamp_radius = max(4.0, 8.0 * scale)
            self._canvas.create_oval(
                x - lamp_radius,
                y - lamp_radius,
                x + lamp_radius,
                y + lamp_radius,
                fill="#ffe6a1",
                outline=self._theme.warning,
                width=2,
            )

        self._canvas.create_line(
            *transform(((-68, 40), (68, 40))),
            fill="#b9c8bf",
            width=max(3, int(5 * scale)),
        )

    def _draw_pitch_scale(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        pitch_deg: float,
    ) -> None:
        """Draw a labeled vertical pitch ladder beside the Jeep."""

        x = center_x - radius * 0.72
        pixels_per_degree = radius / 55.0
        for value in (-30, -20, -10, 0, 10, 20, 30):
            y = center_y - (value - pitch_deg) * pixels_per_degree
            if center_y - radius * 0.68 <= y <= center_y + radius * 0.68:
                self._canvas.create_line(
                    x - 7,
                    y,
                    x + 7,
                    y,
                    fill=self._theme.muted if value else TEXT,
                    width=2,
                )
                self._canvas.create_text(
                    x - 12,
                    y,
                    anchor=tk.E,
                    text=str(value),
                    fill=self._theme.muted,
                    font=("TkFixedFont", 8),
                )
        self._canvas.create_polygon(
            x + 11,
            center_y,
            x + 22,
            center_y - 6,
            x + 22,
            center_y + 6,
            fill=self._theme.warning,
            outline="",
        )

    def _draw_angle_card(
        self,
        x: float,
        y: float,
        width: float,
        title: str,
        value: float | None,
        direction: str,
        warning_deg: float,
    ) -> None:
        height = 150
        self._canvas.create_rectangle(
            x, y, x + width, y + height, fill=self._theme.panel, outline=self._theme.border, width=2
        )
        self._canvas.create_text(
            x + 14,
            y + 16,
            anchor=tk.NW,
            text=title,
            fill=self._theme.muted,
            font=("TkDefaultFont", 11, "bold"),
        )
        if value is None:
            display = "--.-°"
            color = MUTED
        else:
            display = f"{abs(value):.1f}°"
            ratio = abs(value) / warning_deg
            color = RED if ratio >= 1 else AMBER if ratio >= 0.75 else GREEN
        self._canvas.create_text(
            x + width / 2,
            y + 70,
            text=display,
            fill=color,
            font=("TkFixedFont", 30, "bold"),
        )
        self._canvas.create_text(
            x + width / 2,
            y + 121,
            text=direction if value is not None else "--",
            fill=self._theme.text,
            font=("TkDefaultFont", 10, "bold"),
        )

    def _draw_bottom_cards(
        self,
        width: int,
        height: int,
        state: _DashboardState | None,
    ) -> None:
        top = height - 92
        margin = 14
        gap = 8
        labels: list[tuple[str, str]] = []

        if state is None:
            labels.extend(
                (
                    ("FORE / AFT", "--"),
                    ("LATERAL", "--"),
                    ("ALTITUDE", "--"),
                    ("SPEED", "--"),
                    ("GPS COURSE", "--"),
                    ("SATELLITES", "--"),
                )
            )
        else:
            linear = state.linear_acceleration_mps2
            gps = state.gps
            labels.extend(
                (
                    (
                        "FORE / AFT",
                        f"{linear.x:+.2f} m/s²" if linear.x is not None else "--",
                    ),
                    (
                        "LATERAL",
                        f"{linear.y:+.2f} m/s²" if linear.y is not None else "--",
                    ),
                    (
                        "ALTITUDE",
                        (
                            f"{gps.altitude_m:.1f} m"
                            if gps is not None and gps.altitude_m is not None
                            else "--"
                        ),
                    ),
                    (
                        "SPEED",
                        (
                            f"{gps.speed_mps * 2.23694:.1f} mph"
                            if gps is not None and gps.speed_mps is not None
                            else "--"
                        ),
                    ),
                    (
                        "GPS COURSE",
                        (
                            f"{gps.course_deg:.0f}°"
                            if gps is not None and gps.course_deg is not None
                            else "--"
                        ),
                    ),
                    (
                        "SATELLITES",
                        (
                            str(gps.satellites_used)
                            if gps is not None
                            and gps.satellites_used is not None
                            else "--"
                        ),
                    ),
                )
            )

        card_width = (width - 2 * margin - (len(labels) - 1) * gap) / len(labels)
        for index, (label, value) in enumerate(labels):
            x = margin + index * (card_width + gap)
            self._canvas.create_rectangle(
                x,
                top,
                x + card_width,
                height - 10,
                fill=self._theme.panel,
                outline=self._theme.border,
            )
            self._canvas.create_text(
                x + card_width / 2,
                top + 18,
                text=label,
                fill=self._theme.muted,
                font=("TkDefaultFont", 9, "bold"),
            )
            self._canvas.create_text(
                x + card_width / 2,
                top + 51,
                text=value,
                fill=self._theme.text,
                font=("TkFixedFont", 14, "bold"),
            )

    def _request_calibration(self) -> None:
        if self._request_handler is not None:
            self._request_handler.request_stationary_calibration()

    def _request_heading_reset(self) -> None:
        if self._request_handler is not None:
            self._request_handler.request_heading_reset()
