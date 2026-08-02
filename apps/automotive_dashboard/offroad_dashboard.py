"""Rugged Tkinter dashboard for off-road navigation data."""

from __future__ import annotations

import argparse
import math
import tkinter as tk

from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    NavigationState,
)
from hardware_io.imu import Mpu6050Imu


BACKGROUND = "#07100d"
PANEL = "#101d18"
GRID = "#274238"
TEXT = "#e5f2e9"
MUTED = "#8ca398"
GREEN = "#66e38f"
AMBER = "#ffb347"
RED = "#ff5d52"
SKY = "#18344b"
GROUND = "#493825"


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


class OffroadDashboardApp:
    """Display trail-oriented navigation and vehicle attitude information."""

    def __init__(
        self,
        controller: NavigationController,
        update_ms: int,
        pitch_warning_deg: float,
        roll_warning_deg: float,
        calibrate_on_start: bool,
        calibration_samples: int,
        calibration_interval_s: float,
        gps_enabled: bool,
    ) -> None:
        self._controller = controller
        self._update_ms = update_ms
        self._pitch_warning_deg = pitch_warning_deg
        self._roll_warning_deg = roll_warning_deg
        self._calibrate_on_start = calibrate_on_start
        self._calibration_samples = calibration_samples
        self._calibration_interval_s = calibration_interval_s
        self._gps_enabled = gps_enabled
        self._closed = False
        self._state: NavigationState | None = None

        self._root = tk.Tk()
        self._root.title("OpenRoadCode Off-Road Dashboard")
        self._root.geometry("1024x600")
        self._root.minsize(760, 480)
        self._root.configure(bg=BACKGROUND)

        self._canvas = tk.Canvas(
            self._root,
            bg=BACKGROUND,
            highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", lambda _event: self._draw())

        controls = tk.Frame(self._root, bg=PANEL)
        controls.pack(fill=tk.X)
        self._button(
            controls, "CALIBRATE", self._calibrate
        ).pack(side=tk.LEFT, padx=(10, 4), pady=7)
        self._button(
            controls, "ZERO HEADING", self._reset_heading
        ).pack(side=tk.LEFT, padx=4, pady=7)

        self._status = tk.StringVar(value="STARTING")
        tk.Label(
            controls,
            textvariable=self._status,
            fg=GREEN,
            bg=PANEL,
            font=("TkFixedFont", 10, "bold"),
        ).pack(side=tk.RIGHT, padx=14)

        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._root.bind("<Escape>", lambda _event: self._close())
        self._root.bind("q", lambda _event: self._close())
        self._root.bind("c", lambda _event: self._calibrate())
        self._root.bind("h", lambda _event: self._reset_heading())

    @staticmethod
    def _button(
        parent: tk.Widget,
        text: str,
        command: object,
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg="#263d31",
            fg=TEXT,
            activebackground="#355442",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=14,
            font=("TkDefaultFont", 9, "bold"),
        )

    def run(self) -> None:
        try:
            self._controller.start()
        except Exception as exc:
            self._status.set(f"SENSOR ERROR · {exc}")
        else:
            self._status.set("NAVIGATION ONLINE")
            if self._calibrate_on_start:
                self._root.after(150, self._calibrate)
            self._root.after(0, self._poll)
        self._root.mainloop()

    def _poll(self) -> None:
        if self._closed or not self._controller.is_started:
            return
        try:
            self._state = self._controller.read_state()
        except Exception as exc:
            self._status.set(f"NAVIGATION ERROR · {exc}")
            return

        gps = self._state.gps
        if _is_capsized(self._state.pitch_deg, self._state.roll_deg):
            self._status.set(
                "CAPSIZED · CALL THE POLICE? MAYBE THE WINCH CREW FIRST"
            )
        elif self._gps_enabled and gps is None:
            self._status.set("IMU ONLINE · WAITING FOR GPSD")
        elif self._gps_enabled and not gps.has_fix:
            self._status.set("IMU ONLINE · ACQUIRING GPS")
        elif self._controller.calibration is None:
            self._status.set("NAVIGATION ONLINE · CALIBRATION RECOMMENDED")
        else:
            self._status.set("NAVIGATION ONLINE · CALIBRATED")

        self._draw()
        self._root.after(self._update_ms, self._poll)

    def _draw(self) -> None:
        self._canvas.delete("all")
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        state = self._state

        self._draw_header(width, state)

        content_top = 88
        content_bottom = height - 142
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
        self._draw_heading_card(
            width - side_width - 18,
            content_top + 174,
            side_width,
            state,
        )

        self._draw_bottom_cards(width, height, state)

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
            outline=RED,
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
        state: NavigationState | None,
    ) -> None:
        self._canvas.create_rectangle(0, 0, width, 82, fill=PANEL, outline="")
        heading = state.heading_deg if state is not None else 0.0
        heading_text = (
            f"REL {heading:03.0f}°"
            if state is not None
            else "REL ---°"
        )
        self._canvas.create_text(
            width / 2,
            22,
            text=heading_text,
            fill=TEXT,
            font=("TkFixedFont", 22, "bold"),
        )

        pixels_per_degree = max(3.0, width / 180.0)
        for offset in range(-60, 61, 5):
            marker_heading = _normalize_heading(heading + offset)
            x = width / 2 + offset * pixels_per_degree
            major = offset % 15 == 0
            y1 = 52
            y2 = 72 if major else 64
            self._canvas.create_line(x, y1, x, y2, fill=GRID, width=2)
            if major:
                self._canvas.create_text(
                    x,
                    44,
                    text=f"{marker_heading:.0f}",
                    fill=MUTED,
                    font=("TkFixedFont", 9),
                )
        self._canvas.create_polygon(
            width / 2 - 7,
            78,
            width / 2 + 7,
            78,
            width / 2,
            66,
            fill=AMBER,
            outline="",
        )

    def _draw_heading_card(
        self,
        x: float,
        y: float,
        width: float,
        state: NavigationState | None,
    ) -> None:
        """Draw relative heading and optional GPS course from above."""

        height = 164
        self._canvas.create_rectangle(
            x, y, x + width, y + height, fill=PANEL, outline=GRID, width=2
        )
        self._canvas.create_text(
            x + 14,
            y + 14,
            anchor=tk.NW,
            text="HEADING",
            fill=MUTED,
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
            outline=GRID,
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
            fill=GREEN,
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
                fill=AMBER,
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
            outline=GREEN if state is not None else MUTED,
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
            fill=GREEN,
            outline="",
        )

        relative_text = (
            f"REL {heading:03.0f}°" if state is not None else "REL ---°"
        )
        self._canvas.create_text(
            center_x,
            y + height - 10,
            text=relative_text,
            fill=TEXT,
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
            x, y, x + width, y + height, fill=PANEL, outline=GRID, width=2
        )
        self._canvas.create_text(
            x + 14,
            y + 16,
            anchor=tk.NW,
            text="PITCH",
            fill=MUTED,
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
        center_y = y + 145
        half_level = width * 0.38
        self._canvas.create_line(
            center_x - half_level,
            center_y + 25,
            center_x + half_level,
            center_y + 25,
            fill=AMBER,
            width=2,
            dash=(5, 4),
        )
        self._canvas.create_text(
            center_x + half_level,
            center_y + 36,
            anchor=tk.E,
            text="LEVEL",
            fill=AMBER,
            font=("TkDefaultFont", 7, "bold"),
        )

        scale = min(1.0, width / 210.0)

        def transform(
            points: tuple[tuple[float, float], ...],
        ) -> tuple[float, ...]:
            transformed: list[float] = []
            for local_x, local_y in points:
                screen_point = _rotate_screen_point(
                    (local_x * scale, local_y * scale),
                    center_x,
                    center_y,
                    -pitch,
                )
                transformed.extend(screen_point)
            return tuple(transformed)

        # The vehicle faces right, so positive pitch visibly raises its nose.
        body = (
            (-69, -5), (48, -5), (70, 9), (64, 22),
            (-66, 22), (-76, 10),
        )
        cabin = ((-39, -6), (-24, -32), (22, -32), (42, -6))
        window = ((-27, -9), (-17, -26), (15, -26), (29, -9))

        self._canvas.create_polygon(
            *transform(body),
            fill="#263d31",
            outline=TEXT,
            width=2,
            joinstyle=tk.ROUND,
        )
        self._canvas.create_polygon(
            *transform(cabin),
            fill="#263d31",
            outline=TEXT,
            width=2,
        )
        self._canvas.create_polygon(
            *transform(window),
            fill="#102636",
            outline="#7ea3b8",
            width=1,
        )

        for wheel_x in (-48, 47):
            wheel_center_x, wheel_center_y = _rotate_screen_point(
                (wheel_x * scale, 22 * scale),
                center_x,
                center_y,
                -pitch,
            )
            wheel_radius = 13 * scale
            self._canvas.create_oval(
                wheel_center_x - wheel_radius,
                wheel_center_y - wheel_radius,
                wheel_center_x + wheel_radius,
                wheel_center_y + wheel_radius,
                fill="#101411",
                outline="#9bad9f",
                width=2,
            )
            hub_radius = 4 * scale
            self._canvas.create_oval(
                wheel_center_x - hub_radius,
                wheel_center_y - hub_radius,
                wheel_center_x + hub_radius,
                wheel_center_y + hub_radius,
                fill=AMBER,
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
            outline=GRID,
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
            fill=AMBER,
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
                fill=MUTED,
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
                outline=AMBER,
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
                    fill=MUTED if value else TEXT,
                    width=2,
                )
                self._canvas.create_text(
                    x - 12,
                    y,
                    anchor=tk.E,
                    text=str(value),
                    fill=MUTED,
                    font=("TkFixedFont", 8),
                )
        self._canvas.create_polygon(
            x + 11,
            center_y,
            x + 22,
            center_y - 6,
            x + 22,
            center_y + 6,
            fill=AMBER,
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
            x, y, x + width, y + height, fill=PANEL, outline=GRID, width=2
        )
        self._canvas.create_text(
            x + 14,
            y + 16,
            anchor=tk.NW,
            text=title,
            fill=MUTED,
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
            fill=TEXT,
            font=("TkDefaultFont", 10, "bold"),
        )

    def _draw_bottom_cards(
        self,
        width: int,
        height: int,
        state: NavigationState | None,
    ) -> None:
        top = height - 128
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
                    ("FORE / AFT", f"{linear.x:+.2f} m/s²"),
                    ("LATERAL", f"{linear.y:+.2f} m/s²"),
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
                fill=PANEL,
                outline=GRID,
            )
            self._canvas.create_text(
                x + card_width / 2,
                top + 25,
                text=label,
                fill=MUTED,
                font=("TkDefaultFont", 9, "bold"),
            )
            self._canvas.create_text(
                x + card_width / 2,
                top + 66,
                text=value,
                fill=TEXT,
                font=("TkFixedFont", 14, "bold"),
            )

    def _calibrate(self) -> None:
        if not self._controller.is_started:
            self._status.set("SENSOR NOT CONNECTED")
            return
        self._status.set("CALIBRATING · KEEP VEHICLE STILL")
        self._root.update_idletasks()
        try:
            result = self._controller.calibrate_stationary(
                sample_count=self._calibration_samples,
                sample_interval_s=self._calibration_interval_s,
            )
        except Exception as exc:
            self._status.set(f"CALIBRATION ERROR · {exc}")
        else:
            self._status.set(f"CALIBRATED · {result.sample_count} SAMPLES")

    def _reset_heading(self) -> None:
        if self._controller.is_started:
            self._controller.reset_heading()
            self._status.set("RELATIVE HEADING ZEROED")

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._controller.stop()
        self._root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display a trail-oriented off-road vehicle dashboard."
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=Mpu6050Imu.DEFAULT_ADDRESS,
    )
    parser.add_argument("--update-ms", type=int, default=75)
    parser.add_argument("--filter-time-constant", type=float, default=0.5)
    parser.add_argument("--pitch-warning", type=float, default=30.0)
    parser.add_argument("--roll-warning", type=float, default=25.0)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--calibration-samples", type=int, default=100)
    parser.add_argument("--calibration-interval", type=float, default=0.01)
    parser.add_argument("--gps", action="store_true")
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
    args = parser.parse_args()

    if args.update_ms <= 0:
        parser.error("--update-ms must be greater than zero")
    if args.filter_time_constant < 0:
        parser.error("--filter-time-constant must be zero or greater")
    if args.pitch_warning <= 0 or args.roll_warning <= 0:
        parser.error("warning angles must be greater than zero")
    if args.calibration_samples <= 0:
        parser.error("--calibration-samples must be greater than zero")
    if args.calibration_interval < 0:
        parser.error("--calibration-interval must be zero or greater")
    return args


def main() -> int:
    args = parse_args()
    gps_source = None
    if args.gps:
        from hardware_io.gps import GpsReader

        gps_source = GpsdNavigationAdapter(
            GpsReader(host=args.gps_host, port=args.gps_port)
        )

    controller = NavigationController(
        sensor=Mpu6050NavigationAdapter(
            Mpu6050Imu(address=args.address)
        ),
        filter_time_constant_s=args.filter_time_constant,
        gps_source=gps_source,
    )
    app = OffroadDashboardApp(
        controller=controller,
        update_ms=args.update_ms,
        pitch_warning_deg=args.pitch_warning,
        roll_warning_deg=args.roll_warning,
        calibrate_on_start=args.calibrate,
        calibration_samples=args.calibration_samples,
        calibration_interval_s=args.calibration_interval,
        gps_enabled=args.gps,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
