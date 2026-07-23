import math
import tkinter as tk

from apps.common.instruments.gauge_config import GaugeConfig
from apps.common.instruments.gauge_style  import GaugeStyle


class GaugeWidget(tk.Canvas):
    """Render a single analog-style telemetry gauge on a Tk canvas."""
    def __init__(
        self,
        parent,
        config: GaugeConfig,
        style: GaugeStyle | None = None,
    ) -> None:
        self._config = config
        self._style = style or GaugeStyle()
        self._value: float | None = None

        super().__init__(
            parent,
            width=config.width,
            height=config.height,
            bg=self._style.face,
            highlightthickness=0,
        )

        self.draw()

    def set_value(self, value: float | None) -> None:
        """Set the displayed value and redraw the gauge."""
        self._value = value
        self.draw()

    def draw(self) -> None:
        """Redraw the complete gauge using its current value and style."""
        self.delete("all")

        width = self._config.width
        height = self._config.height

        cx = width / 2
        cy = height * 0.85
        radius = min(width * 0.42, height * 0.72)

        start_angle = 210.0
        sweep_angle = 240.0

        self.create_arc(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            start=-30,
            extent=240,
            style=tk.ARC,
            width=8,
            outline=self._style.arc,
        )

        self.create_text(
            cx,
            16,
            text=self._config.title,
            fill=self._style.title,
            font=("Arial", 13, "bold"),
        )

        if self._value is None:
            display = "--"
            normalized = 0.0
        else:
            clamped = max(
                self._config.min_value,
                min(self._config.max_value, self._value),
            )
            normalized = (
                (clamped - self._config.min_value)
                / (self._config.max_value - self._config.min_value)
            )
            display = f"{self._value:.{self._config.precision}f}"

        angle_deg = start_angle - normalized * sweep_angle
        angle_rad = math.radians(angle_deg)

        needle_len = radius * 0.78
        nx = cx + needle_len * math.cos(angle_rad)
        ny = cy - needle_len * math.sin(angle_rad)

        self.create_line(
            cx,
            cy,
            nx,
            ny,
            fill=self._style.needle,
            width=4,
            capstyle=tk.ROUND,
        )

        self.create_oval(
            cx - 5,
            cy - 5,
            cx + 5,
            cy + 5,
            fill=self._style.needle,
            outline="",
        )

        self.create_text(
            cx,
            cy - radius * 0.35,
            text=display,
            fill=self._style.value,
            font=("Arial", 22, "bold"),
        )

        self.create_text(
            cx,
            cy - radius * 0.12,
            text=self._config.unit,
            fill=self._style.unit,
            font=("Arial", 10),
        )

        self.create_text(
            cx - radius * 0.75,
            cy + 4,
            text=f"{self._config.min_value:g}",
            fill=self._style.tick,
            font=("Arial", 9),
        )

        self.create_text(
            cx + radius * 0.75,
            cy + 4,
            text=f"{self._config.max_value:g}",
            fill=self._style.tick,
            font=("Arial", 9),
        )
