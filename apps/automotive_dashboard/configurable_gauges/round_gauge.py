"""SRT-era inspired automotive gauges for Tkinter."""

from __future__ import annotations

import math
import tkinter as tk
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GaugeStyle:
    """Shared colours for the instrument cluster."""

    face_color: str = "#f2efe5"
    face_shadow: str = "#9b9c99"
    background_color: str = "#090a0b"
    foreground_color: str = "#17191b"
    accent_color: str = "#d51f2b"
    muted_color: str = "#686b6d"
    bezel_dark: str = "#202326"
    bezel_mid: str = "#9da1a2"
    display_color: str = "#181b1c"
    display_text: str = "#ff694f"


class _ValueGauge(tk.Canvas):
    """Common value and connection handling for canvas gauges."""

    def __init__(self, master: tk.Misc, *, style: GaugeStyle, **kwargs: object) -> None:
        self._style = style
        self._value: float | None = None
        self._connected = True
        super().__init__(
            master,
            background=style.background_color,
            highlightthickness=0,
            **kwargs,
        )
        self.bind("<Configure>", self._on_resize)
        self.after_idle(self._draw)

    @property
    def value(self) -> float | None:
        return self._value

    def set_value(self, value: float | int | None) -> None:
        self._value = None if value is None else float(value)
        self._draw()

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self._draw()

    def _on_resize(self, _event: tk.Event[tk.Misc]) -> None:
        self._draw()

    def _draw(self) -> None:
        raise NotImplementedError


class RoundGauge(_ValueGauge):
    """Layered analog dial inspired by early-2000s performance clusters."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
        unit: str,
        minimum: float,
        maximum: float,
        major_step: float,
        caution_start: float | None = None,
        danger_start: float | None = None,
        start_angle: float = 135.0,
        sweep_angle: float = 270.0,
        precision: int = 0,
        style: GaugeStyle | None = None,
        size: int = 220,
        **kwargs: object,
    ) -> None:
        if maximum <= minimum:
            raise ValueError("maximum must be greater than minimum")
        if major_step <= 0:
            raise ValueError("major_step must be greater than zero")
        self._title = title
        self._unit = unit
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        self._major_step = float(major_step)
        if sweep_angle <= 0 or sweep_angle > 360:
            raise ValueError("sweep_angle must be between 0 and 360")
        self._caution_start = caution_start
        self._danger_start = danger_start
        self._start_angle = start_angle
        self._sweep_angle = sweep_angle
        self._precision = precision
        super().__init__(
            master,
            style=style or GaugeStyle(),
            width=size,
            height=size,
            **kwargs,
        )

    def _draw(self) -> None:
        self.delete("all")
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        size = min(width, height)
        cx, cy = width / 2, height / 2
        radius = size * 0.46

        # Concentric rings fake the depth and highlight of a metal instrument bezel.
        rings = (
            (1.00, "#08090a"),
            (0.975, "#282b2d"),
            (0.935, "#707476"),
            (0.905, "#e3e4e1"),
            (0.875, "#767a7c"),
            (0.845, "#151719"),
            (0.815, self._style.face_shadow),
            (0.792, self._style.face_color),
        )
        for scale, color in rings:
            r = radius * scale
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=color, outline=color)

        # A restrained face highlight makes the dial less like a flat vector circle.
        r = radius * 0.755
        self.create_arc(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            start=25,
            extent=130,
            style=tk.ARC,
            outline="#ffffff",
            width=max(2, int(size * 0.008)),
        )
        self._draw_operating_bands(cx, cy, radius)
        self._draw_ticks(cx, cy, radius)
        self._draw_labels(cx, cy, radius)
        self._draw_needle(cx, cy, radius)
        self._draw_center(cx, cy, radius)

    def _draw_operating_bands(self, cx: float, cy: float, radius: float) -> None:
        """Draw only configured caution and danger bands on the outer scale."""
        r = radius * 0.705
        bands = (
            (self._caution_start, self._danger_start or self._maximum, "#e4a514"),
            (self._danger_start, self._maximum, self._style.accent_color),
        )
        for start_value, end_value, color in bands:
            if start_value is None:
                continue
            start_value = max(self._minimum, min(self._maximum, start_value))
            end_value = max(start_value, min(self._maximum, end_value))
            start_angle = self._value_to_angle(start_value)
            end_angle = self._value_to_angle(end_value)
            self.create_arc(
                cx - r,
                cy - r,
                cx + r,
                cy + r,
                start=-start_angle,
                extent=-(end_angle - start_angle),
                style=tk.ARC,
                outline=color,
                width=max(5, int(radius * 0.070)),
            )

    def _draw_ticks(self, cx: float, cy: float, radius: float) -> None:
        minor_step = self._major_step / 5.0
        count = int(round((self._maximum - self._minimum) / minor_step))
        for index in range(count + 1):
            value = self._minimum + index * minor_step
            is_major = index % 5 == 0
            angle = math.radians(self._value_to_angle(value))
            outer = radius * 0.715
            inner = radius * (0.555 if is_major else 0.625)
            tick_color = self._tick_color(value)
            self.create_line(
                cx + inner * math.cos(angle),
                cy + inner * math.sin(angle),
                cx + outer * math.cos(angle),
                cy + outer * math.sin(angle),
                fill=tick_color,
                width=max(1, int(radius * (0.031 if is_major else 0.013))),
            )
            if is_major:
                label_radius = radius * 0.455
                self.create_text(
                    cx + label_radius * math.cos(angle),
                    cy + label_radius * math.sin(angle),
                    text=self._format_tick(value),
                    fill=self._style.foreground_color,
                    font=("DejaVu Sans Condensed", max(8, int(radius * 0.115)), "bold"),
                )

    def _draw_labels(self, cx: float, cy: float, radius: float) -> None:
        self.create_text(
            cx,
            cy - radius * 0.22,
            text=self._title.upper(),
            fill=self._style.foreground_color,
            font=("DejaVu Sans Condensed", max(9, int(radius * 0.12)), "bold"),
        )
        self.create_text(
            cx,
            cy - radius * 0.055,
            text=self._unit.upper(),
            fill=self._style.muted_color,
            font=("DejaVu Sans", max(6, int(radius * 0.075)), "bold"),
        )
        value_text = "--" if self._value is None else f"{self._value:.{self._precision}f}"
        if not self._connected:
            value_text = "OFF"
        self.create_text(
            cx,
            cy + radius * 0.13,
            text="PERFORMANCE",
            fill="#8a8881",
            font=("DejaVu Sans Condensed", max(5, int(radius * 0.055)), "bold"),
        )
        box_w, box_h = radius * 0.58, radius * 0.18
        box_y = cy + radius * 0.61
        self.create_rectangle(
            cx - box_w / 2,
            box_y - box_h / 2,
            cx + box_w / 2,
            box_y + box_h / 2,
            fill=self._style.display_color,
            outline="#6f7373",
            width=max(2, int(radius * 0.016)),
        )
        self.create_text(
            cx,
            box_y,
            text=value_text,
            fill=self._style.display_text if self._connected else self._style.muted_color,
            font=("DejaVu Sans Mono", max(8, int(radius * 0.12)), "bold"),
        )

    def _draw_needle(self, cx: float, cy: float, radius: float) -> None:
        value = self._minimum if self._value is None else self._value
        value = max(self._minimum, min(self._maximum, value))
        angle = math.radians(self._value_to_angle(value))
        color = self._style.accent_color if self._connected and self._value is not None else self._style.muted_color
        tip = radius * 0.65
        tail = radius * 0.12
        perp = angle + math.pi / 2
        half_width = radius * 0.042
        points = (
            cx + tip * math.cos(angle),
            cy + tip * math.sin(angle),
            cx - tail * math.cos(angle) + half_width * math.cos(perp),
            cy - tail * math.sin(angle) + half_width * math.sin(perp),
            cx - tail * math.cos(angle) - half_width * math.cos(perp),
            cy - tail * math.sin(angle) - half_width * math.sin(perp),
        )
        self.create_polygon(*points, fill="#760d14", outline="#f26a70", width=1)
        shorter = radius * 0.56
        self.create_line(
            cx,
            cy,
            cx + shorter * math.cos(angle),
            cy + shorter * math.sin(angle),
            fill=color,
            width=max(3, int(radius * 0.035)),
        )

    def _draw_center(self, cx: float, cy: float, radius: float) -> None:
        for scale, color in (
            (0.125, "#202326"),
            (0.105, "#c7c9c7"),
            (0.080, "#2c2e2f"),
            (0.040, "#dedfda"),
        ):
            hub = radius * scale
            self.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill=color, outline=color)

    def _value_to_angle(self, value: float) -> float:
        ratio = (value - self._minimum) / (self._maximum - self._minimum)
        return self._start_angle + ratio * self._sweep_angle

    def _tick_color(self, value: float) -> str:
        if self._danger_start is not None and value >= self._danger_start:
            return self._style.accent_color
        if self._caution_start is not None and value >= self._caution_start:
            return "#c88b0d"
        return self._style.foreground_color

    @staticmethod
    def _format_tick(value: float) -> str:
        return str(int(round(value))) if math.isclose(value, round(value)) else f"{value:g}"


class LinearGauge(_ValueGauge):
    """Compact rectangular gauge for temperatures and secondary telemetry."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
        unit: str,
        minimum: float,
        maximum: float,
        caution_low: float | None = None,
        danger_low: float | None = None,
        caution_high: float | None = None,
        danger_high: float | None = None,
        icon: str | None = None,
        precision: int = 0,
        style: GaugeStyle | None = None,
        width: int = 220,
        height: int = 110,
        **kwargs: object,
    ) -> None:
        if maximum <= minimum:
            raise ValueError("maximum must be greater than minimum")
        self._title, self._unit = title, unit
        self._minimum, self._maximum = float(minimum), float(maximum)
        self._caution_low, self._danger_low = caution_low, danger_low
        self._caution_high, self._danger_high = caution_high, danger_high
        self._icon, self._precision = icon, precision
        super().__init__(
            master,
            style=style or GaugeStyle(),
            width=width,
            height=height,
            **kwargs,
        )

    def _draw(self) -> None:
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        pad = max(7, min(w, h) * 0.08)
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill="#08090a",
            outline="#626668",
            width=2,
        )
        self.create_rectangle(
            pad * 1.35,
            pad * 1.35,
            w - pad * 1.35,
            h - pad * 1.35,
            fill="#111315",
            outline="#2e3133",
        )

        icon_x = pad * 2
        icon_y = h * 0.30
        if self._icon:
            self._draw_icon(icon_x, icon_y, h * 0.16)
        self.create_text(
            icon_x + (h * 0.22 if self._icon else 0),
            h * 0.30,
            anchor="w",
            text=self._title.upper(),
            fill="#f0f0ed",
            font=("DejaVu Sans Condensed", max(8, int(h * 0.12)), "bold"),
        )
        value_text = "--" if self._value is None else f"{self._value:.{self._precision}f}"
        if not self._connected:
            value_text = "OFF"
        self.create_text(
            w - pad * 2,
            h * 0.30,
            anchor="e",
            text=f"{value_text} {self._unit}",
            fill=self._value_color(),
            font=("DejaVu Sans Mono", max(8, int(h * 0.13)), "bold"),
        )

        x1, x2, y = pad * 2, w - pad * 2, h * 0.64
        bar_h = max(10, h * 0.14)
        # Individual red dashes resemble a back-lit segmented auxiliary gauge.
        segment_count = 18
        gap = max(2, (x2 - x1) * 0.008)
        segment_width = (x2 - x1 - gap * (segment_count - 1)) / segment_count
        active_ratio = 0.0
        if self._value is not None and self._connected:
            clamped = max(self._minimum, min(self._maximum, self._value))
            active_ratio = (clamped - self._minimum) / (self._maximum - self._minimum)
        for index in range(segment_count):
            sx1 = x1 + index * (segment_width + gap)
            sx2 = sx1 + segment_width
            is_active = (index + 1) / segment_count <= active_ratio + 1 / segment_count
            segment_value = self._minimum + (
                (self._maximum - self._minimum) * index / (segment_count - 1)
            )
            segment_color = self._range_color(segment_value)
            inactive_color = {
                "#ffffff": "#303234",
                "#f0b323": "#4e3d12",
                "#ff3446": "#57131b",
            }[segment_color]
            color = segment_color if is_active else inactive_color
            self.create_rectangle(
                sx1,
                y - bar_h / 2,
                sx2,
                y + bar_h / 2,
                fill=color,
                outline="",
            )
        if self._value is not None and self._connected:
            marker_x = self._value_x(self._value, x1, x2)
            self.create_polygon(
                marker_x, y - bar_h,
                marker_x - bar_h * 0.45, y - bar_h * 1.65,
                marker_x + bar_h * 0.45, y - bar_h * 1.65,
                fill=self._style.accent_color,
                outline="#7b1017",
            )
            self.create_line(marker_x, y - bar_h / 2, marker_x, y + bar_h / 2, fill="#ffffff", width=2)
        for index in range(6):
            x = x1 + (x2 - x1) * index / 5
            self.create_line(x, y + bar_h / 2, x, y + bar_h, fill="#a92b34")
        self.create_text(x1, h * 0.84, anchor="w", text=self._format_end(self._minimum), fill="#a9acad", font=("DejaVu Sans", max(7, int(h * 0.08))))
        self.create_text(x2, h * 0.84, anchor="e", text=self._format_end(self._maximum), fill="#a9acad", font=("DejaVu Sans", max(7, int(h * 0.08))))

    def _value_x(self, value: float, x1: float, x2: float) -> float:
        clamped = max(self._minimum, min(self._maximum, value))
        return x1 + (clamped - self._minimum) / (self._maximum - self._minimum) * (x2 - x1)

    def _value_color(self) -> str:
        if not self._connected or self._value is None:
            return self._style.muted_color
        return self._range_color(self._value)

    def _range_color(self, value: float) -> str:
        if (
            (self._danger_low is not None and value <= self._danger_low)
            or (self._danger_high is not None and value >= self._danger_high)
        ):
            return "#ff3446"
        if (
            (self._caution_low is not None and value <= self._caution_low)
            or (self._caution_high is not None and value >= self._caution_high)
        ):
            return "#f0b323"
        return "#ffffff"

    @staticmethod
    def _format_end(value: float) -> str:
        return str(int(value)) if math.isclose(value, round(value)) else f"{value:g}"

    def _draw_icon(self, x: float, y: float, size: float) -> None:
        """Draw small dashboard-style symbols without external image assets."""
        color = "#f0f0ed"
        width = max(1, int(size * 0.12))
        if self._icon == "coolant":
            bulb = size * 0.22
            self.create_line(x, y - size * 0.35, x, y + size * 0.18, fill=color, width=width)
            self.create_oval(
                x - bulb,
                y + size * 0.05,
                x + bulb,
                y + size * 0.49,
                outline=color,
                width=width,
            )
            for offset in (-0.32, 0.05, 0.42):
                wave_x = x + size * offset
                self.create_arc(
                    wave_x,
                    y + size * 0.22,
                    wave_x + size * 0.42,
                    y + size * 0.52,
                    start=20,
                    extent=140,
                    style=tk.ARC,
                    outline=color,
                    width=width,
                )
        elif self._icon == "voltage":
            half_w, half_h = size * 0.55, size * 0.34
            self.create_rectangle(
                x - half_w,
                y - half_h,
                x + half_w,
                y + half_h,
                outline=color,
                width=width,
            )
            self.create_line(x - size * 0.30, y - half_h, x - size * 0.30, y - size * 0.52, fill=color, width=width)
            self.create_line(x + size * 0.30, y - half_h, x + size * 0.30, y - size * 0.52, fill=color, width=width)
            self.create_text(x - size * 0.28, y, text="+", fill=color, font=("DejaVu Sans", max(7, int(size * 0.45)), "bold"))
            self.create_text(x + size * 0.28, y, text="−", fill=color, font=("DejaVu Sans", max(7, int(size * 0.45)), "bold"))
        elif self._icon == "fuel":
            half_w, half_h = size * 0.42, size * 0.48
            self.create_rectangle(
                x - half_w,
                y - half_h,
                x + half_w,
                y + half_h,
                outline=color,
                width=width,
            )
            self.create_rectangle(
                x - size * 0.25,
                y - size * 0.31,
                x + size * 0.25,
                y - size * 0.03,
                outline=color,
                width=width,
            )
            self.create_line(
                x + half_w,
                y - size * 0.28,
                x + size * 0.68,
                y - size * 0.08,
                x + size * 0.68,
                y + size * 0.42,
                fill=color,
                width=width,
            )


class MetricTile(_ValueGauge):
    """Compact red digital readout for cumulative and calculated values."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        title: str,
        unit: str,
        precision: int = 0,
        style: GaugeStyle | None = None,
        width: int = 210,
        height: int = 105,
        **kwargs: object,
    ) -> None:
        self._title, self._unit, self._precision = title, unit, precision
        super().__init__(
            master,
            style=style or GaugeStyle(),
            width=width,
            height=height,
            **kwargs,
        )

    def _draw(self) -> None:
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        pad = max(7, min(w, h) * 0.08)
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill="#0a0c0d",
            outline="#5e6263",
            width=2,
        )
        self.create_text(
            pad * 1.8,
            h * 0.30,
            anchor="w",
            text=self._title.upper(),
            fill="#c8cbca",
            font=("DejaVu Sans Condensed", max(8, int(h * 0.105)), "bold"),
        )
        value = "--" if self._value is None else f"{self._value:.{self._precision}f}"
        if not self._connected:
            value = "OFF"
        self.create_text(
            pad * 1.8,
            h * 0.64,
            anchor="w",
            text=value,
            fill=self._style.display_text if self._connected else self._style.muted_color,
            font=("DejaVu Sans Mono", max(11, int(h * 0.19)), "bold"),
        )
        self.create_text(
            w - pad * 1.8,
            h * 0.64,
            anchor="e",
            text=self._unit,
            fill="#85898a",
            font=("DejaVu Sans Condensed", max(7, int(h * 0.09)), "bold"),
        )


class TirePressurePanel(_ValueGauge):
    """Four-corner tire-pressure display with per-tire warning colours."""

    TIRE_KEYS = ("front_left", "front_right", "rear_left", "rear_right")

    def __init__(
        self,
        master: tk.Misc,
        *,
        caution_low: float = 30.0,
        danger_low: float = 26.0,
        caution_high: float = 40.0,
        danger_high: float = 44.0,
        style: GaugeStyle | None = None,
        width: int = 440,
        height: int = 170,
        **kwargs: object,
    ) -> None:
        self._pressures: dict[str, float] = {}
        self._caution_low, self._danger_low = caution_low, danger_low
        self._caution_high, self._danger_high = caution_high, danger_high
        super().__init__(
            master,
            style=style or GaugeStyle(),
            width=width,
            height=height,
            **kwargs,
        )

    def set_value(self, value: object) -> None:
        if isinstance(value, dict):
            self._pressures = {
                str(key): float(pressure)
                for key, pressure in value.items()
                if pressure is not None
            }
        elif isinstance(value, (tuple, list)) and len(value) == 4:
            self._pressures = dict(zip(self.TIRE_KEYS, map(float, value)))
        else:
            self._pressures = {}
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        pad = max(8, min(w, h) * 0.06)
        self.create_rectangle(
            pad, pad, w - pad, h - pad,
            fill="#090b0c", outline="#626668", width=2,
        )
        self.create_text(
            w / 2, h * 0.16, text="TIRE PRESSURE  •  PSI",
            fill="#d8dad9",
            font=("DejaVu Sans Condensed", max(8, int(h * 0.075)), "bold"),
        )
        # Simplified top view of the car locates each pressure spatially.
        self.create_polygon(
            w * 0.43, h * 0.28, w * 0.57, h * 0.28,
            w * 0.61, h * 0.78, w * 0.39, h * 0.78,
            fill="#1e2123", outline="#747879", width=2,
        )
        positions = {
            "front_left": (w * 0.25, h * 0.38, "LF"),
            "front_right": (w * 0.75, h * 0.38, "RF"),
            "rear_left": (w * 0.25, h * 0.70, "LR"),
            "rear_right": (w * 0.75, h * 0.70, "RR"),
        }
        for key, (x, y, label) in positions.items():
            pressure = self._pressures.get(key)
            text = "--" if pressure is None else f"{pressure:.0f}"
            color = self._pressure_color(pressure)
            self.create_text(
                x, y, text=f"{label}  {text}", fill=color,
                font=("DejaVu Sans Mono", max(9, int(h * 0.105)), "bold"),
            )

    def _pressure_color(self, pressure: float | None) -> str:
        if not self._connected or pressure is None:
            return self._style.muted_color
        if pressure <= self._danger_low or pressure >= self._danger_high:
            return "#ff3446"
        if pressure <= self._caution_low or pressure >= self._caution_high:
            return "#f0b323"
        return "#ffffff"

class GearIndicator(_ValueGauge):
    """Large, glanceable manual-transmission gear indicator."""

    VALID_GEARS = {"R", "N", "1", "2", "3", "4", "5", "6"}

    def __init__(
        self,
        master: tk.Misc,
        *,
        style: GaugeStyle | None = None,
        width: int = 150,
        height: int = 220,
        **kwargs: object,
    ) -> None:
        self._gear = "N"
        super().__init__(
            master,
            style=style or GaugeStyle(),
            width=width,
            height=height,
            **kwargs,
        )

    def set_value(self, value: object) -> None:
        if value is None:
            self._gear = "—"
        else:
            normalized = str(value).strip().upper()
            self._gear = normalized if normalized in self.VALID_GEARS else "—"
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        pad = max(8, min(w, h) * 0.06)
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill="#08090a",
            outline="#85898a",
            width=3,
        )
        self.create_text(
            w / 2,
            h * 0.19,
            text="GEAR",
            fill="#d9dbd9",
            font=("DejaVu Sans Condensed", max(9, int(h * 0.075)), "bold"),
        )
        gear_color = "#ff3143" if self._connected else self._style.muted_color
        self.create_text(
            w / 2,
            h * 0.53,
            text=self._gear if self._connected else "—",
            fill=gear_color,
            font=("DejaVu Sans", max(30, int(h * 0.34)), "bold"),
        )
        self.create_text(
            w / 2,
            h * 0.86,
            text="R  •  1  2  3  4  5  6",
            fill="#747879",
            font=("DejaVu Sans Condensed", max(6, int(h * 0.042)), "bold"),
        )


class DiagnosticsPanel(_ValueGauge):
    """Compact check-engine and diagnostic-trouble-code reporter."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        style: GaugeStyle | None = None,
        width: int = 440,
        height: int = 118,
        **kwargs: object,
    ) -> None:
        self._codes: tuple[str, ...] | None = None
        self._mil_on: bool | None = None
        super().__init__(
            master,
            style=style or GaugeStyle(),
            width=width,
            height=height,
            **kwargs,
        )

    def set_value(self, value: object) -> None:
        if value is None:
            self._codes = None
        elif isinstance(value, str):
            self._codes = (value,)
        else:
            try:
                self._codes = tuple(str(code) for code in value)  # type: ignore[union-attr]
            except TypeError:
                self._codes = (str(value),)
        self._draw()

    def set_diagnostics(self, codes: object, mil_on: bool | None) -> None:
        self._mil_on = mil_on
        self.set_value(codes)

    def _draw(self) -> None:
        self.delete("all")
        w, h = max(1, self.winfo_width()), max(1, self.winfo_height())
        pad = max(7, min(w, h) * 0.07)
        self.create_rectangle(
            pad,
            pad,
            w - pad,
            h - pad,
            fill="#0b0d0e",
            outline="#626668",
            width=2,
        )
        self._draw_engine_icon(pad * 2.2, h * 0.47, h * 0.22)

        if not self._connected:
            status, color, detail = "DIAGNOSTICS OFFLINE", "#777b7c", "OBD-II adapter unavailable"
        elif self._codes is None and self._mil_on is None:
            status, color, detail = "DIAGNOSTICS UNAVAILABLE", "#f0b323", "Awaiting Mode 03 / MIL status"
        elif self._mil_on or self._codes:
            status, color = "CHECK ENGINE", "#ff3446"
            detail = "  ".join(self._codes or ("MIL ACTIVE",))
        else:
            status, color, detail = "ENGINE SYSTEMS OK", "#ffffff", "No stored trouble codes"

        self.create_text(
            pad * 4.6,
            h * 0.35,
            anchor="w",
            text=status,
            fill=color,
            font=("DejaVu Sans Condensed", max(9, int(h * 0.12)), "bold"),
        )
        self.create_text(
            pad * 4.6,
            h * 0.62,
            anchor="w",
            text=detail,
            fill="#aeb1b1",
            font=("DejaVu Sans Mono", max(7, int(h * 0.085))),
        )

    def _draw_engine_icon(self, x: float, y: float, size: float) -> None:
        color = "#ffb21a" if self._mil_on else "#b7b9b8"
        width = max(2, int(size * 0.10))
        points = (
            x - size * 0.65, y - size * 0.35,
            x + size * 0.35, y - size * 0.35,
            x + size * 0.55, y - size * 0.12,
            x + size * 0.55, y + size * 0.35,
            x - size * 0.55, y + size * 0.35,
            x - size * 0.72, y + size * 0.10,
        )
        self.create_polygon(*points, fill="", outline=color, width=width)
        self.create_line(x - size * 0.28, y - size * 0.36, x - size * 0.28, y - size * 0.62, fill=color, width=width)
        self.create_line(x + size * 0.18, y - size * 0.36, x + size * 0.18, y - size * 0.58, fill=color, width=width)
