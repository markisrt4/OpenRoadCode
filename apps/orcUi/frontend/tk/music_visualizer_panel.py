# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Music visualizer panel for the integrated OpenRoadCode UI.

This first ORC UI version deliberately uses a simulated analysis source.  The
renderer therefore has no PipeWire, Spotify, song-recognition, or lighting
runtime dependencies.  Those services can be attached later without changing
the Tk rendering surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
import tkinter as tk
from tkinter import ttk
from typing import Callable

from ui.music_visualizer import MusicVisualizationMode

BG = "#05090d"
PANEL = "#0b1117"
CARD = "#0d141b"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
BLUE = "#168bd1"
RED = "#f15a16"
GREEN = "#84ce1f"

_MODE_LABELS = {
    MusicVisualizationMode.SPECTRUM: "Spectrum",
    MusicVisualizationMode.ORBITING_PLANETS: "Orbiting Planets",
    MusicVisualizationMode.ELECTRIC_FREEWAY: "Electric Freeway",
    MusicVisualizationMode.EXPLOSION_FIELD: "Explosion Field",
    MusicVisualizationMode.STAR_DANCE: "Star Dance",
    MusicVisualizationMode.ELECTRIC_RINGS: "Electric Rings",
    MusicVisualizationMode.NEON_RIBBON: "Neon Ribbon",
    MusicVisualizationMode.KALEIDOSCOPE: "Kaleidoscope",
}
_LABEL_MODES = {label: mode for mode, label in _MODE_LABELS.items()}


@dataclass(frozen=True, slots=True)
class VisualizerFrame:
    """Small frontend-facing snapshot produced by an audio-analysis source."""

    level: float
    bass: float
    mid: float
    treble: float
    spectrum: tuple[float, ...]


class MusicVisualizerPanel(tk.Frame):
    """Render OpenRoadCode music visualizations inside a Tk parent."""

    FRAME_MS = 33

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None] | None = None,
        simulate: bool = True,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._on_back = on_back
        self._simulate = simulate
        self._running = True
        self._phase = 0.0
        self._mode = MusicVisualizationMode.SPECTRUM
        self._mode_name = tk.StringVar(value=_MODE_LABELS[self._mode])
        self._frame = VisualizerFrame(0.0, 0.0, 0.0, 0.0, (0.0,) * 24)
        self._stars = [
            (random.random(), random.random(), random.uniform(0.5, 1.8))
            for _ in range(90)
        ]
        self._particles: list[list[float]] = []
        self._build()
        if self._simulate:
            self.after(self.FRAME_MS, self._simulation_tick)

    @property
    def visualization_mode(self) -> MusicVisualizationMode:
        return self._mode

    def set_visualization_mode(self, mode: MusicVisualizationMode) -> None:
        self._mode = mode
        self._mode_name.set(_MODE_LABELS[mode])
        self._draw()

    def set_analysis_frame(self, frame: VisualizerFrame) -> None:
        """Present one audio-analysis snapshot."""
        self._frame = frame
        self._phase += 0.065 + frame.level * 0.12
        self._draw()

    def close(self) -> None:
        self._running = False

    def destroy(self) -> None:
        self.close()
        super().destroy()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(
            self,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
            padx=10,
            pady=8,
        )
        header.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 6))
        header.grid_columnconfigure(2, weight=1)

        if self._on_back is not None:
            tk.Button(
                header,
                text="‹ HOME",
                command=self._on_back,
                bg="#101820",
                fg=TEXT,
                activebackground="#182530",
                activeforeground=TEXT,
                relief=tk.FLAT,
                font=("Sans", 10, "bold"),
                padx=12,
                pady=6,
            ).grid(row=0, column=0, padx=(0, 10))

        tk.Label(
            header,
            text="MUSIC VISUALIZER",
            bg=PANEL,
            fg=BLUE,
            font=("Sans", 12, "bold"),
        ).grid(row=0, column=1, sticky="w")

        tk.Label(
            header,
            text="SIMULATED AUDIO" if self._simulate else "AUDIO INPUT",
            bg=PANEL,
            fg=GREEN if self._simulate else MUTED,
            font=("Sans", 9, "bold"),
        ).grid(row=0, column=2, padx=16, sticky="e")

        picker = ttk.Combobox(
            header,
            textvariable=self._mode_name,
            values=tuple(_MODE_LABELS.values()),
            state="readonly",
            width=19,
        )
        picker.grid(row=0, column=3, sticky="e")
        picker.bind("<<ComboboxSelected>>", self._mode_changed)

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(
            body,
            bg="#020509",
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.bind("<Configure>", lambda _event: self._draw())

        self._status = tk.Label(
            body,
            text="",
            bg="#020509",
            fg="#72818d",
            font=("Monospace", 8),
        )
        self._status.place(relx=0.01, rely=0.985, anchor="sw")

    def _mode_changed(self, _event: object | None = None) -> None:
        self.set_visualization_mode(_LABEL_MODES[self._mode_name.get()])

    def _simulation_tick(self) -> None:
        if not self._running or not self.winfo_exists():
            return

        t = self._phase
        bass = self._clamp(0.48 + 0.32 * math.sin(t * 1.17) + random.uniform(-0.10, 0.10))
        mid = self._clamp(0.42 + 0.28 * math.sin(t * 1.71 + 1.3) + random.uniform(-0.08, 0.08))
        treble = self._clamp(0.38 + 0.30 * math.sin(t * 2.37 + 2.1) + random.uniform(-0.09, 0.09))
        level = self._clamp((bass * 0.42) + (mid * 0.36) + (treble * 0.22))

        spectrum = tuple(
            self._clamp(
                level * 0.34
                + 0.30 * math.sin(t * (0.8 + index * 0.025) + index * 0.47)
                + 0.24 * math.sin(t * 1.9 + index * 0.23)
                + random.uniform(-0.08, 0.08)
            )
            for index in range(24)
        )
        self.set_analysis_frame(VisualizerFrame(level, bass, mid, treble, spectrum))
        self.after(self.FRAME_MS, self._simulation_tick)

    def _draw(self) -> None:
        if not hasattr(self, "_canvas"):
            return
        canvas = self._canvas
        canvas.delete("all")
        width = max(2, canvas.winfo_width())
        height = max(2, canvas.winfo_height())

        renderer = {
            MusicVisualizationMode.SPECTRUM: self._draw_spectrum,
            MusicVisualizationMode.ORBITING_PLANETS: self._draw_planets,
            MusicVisualizationMode.ELECTRIC_FREEWAY: self._draw_freeway,
            MusicVisualizationMode.EXPLOSION_FIELD: self._draw_explosion,
            MusicVisualizationMode.STAR_DANCE: self._draw_stars,
            MusicVisualizationMode.ELECTRIC_RINGS: self._draw_rings,
            MusicVisualizationMode.NEON_RIBBON: self._draw_ribbon,
            MusicVisualizationMode.KALEIDOSCOPE: self._draw_kaleidoscope,
        }[self._mode]
        renderer(width, height)
        self._status.configure(
            text=(
                f"LEVEL {self._frame.level:0.2f}   "
                f"BASS {self._frame.bass:0.2f}   "
                f"MID {self._frame.mid:0.2f}   "
                f"TREBLE {self._frame.treble:0.2f}"
            )
        )

    def _draw_spectrum(self, width: int, height: int) -> None:
        values = self._frame.spectrum
        base = height * 0.90
        gap = max(2.0, width / 430.0)
        bar_width = max(2.0, (width - gap * (len(values) + 1)) / len(values))
        for index, value in enumerate(values):
            x0 = gap + index * (bar_width + gap)
            y0 = base - value * height * 0.74
            color = self._gradient(index / max(1, len(values) - 1))
            self._canvas.create_rectangle(x0, y0, x0 + bar_width, base, fill=color, outline="")
            self._canvas.create_oval(x0, y0 - 2, x0 + bar_width, y0 + 3, fill="#eaffff", outline="")
        self._canvas.create_line(0, base, width, base, fill="#274154", width=2)

    def _draw_planets(self, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        for sx, sy, size in self._stars:
            self._canvas.create_oval(sx * width, sy * height, sx * width + size, sy * height + size, fill="#a9cfff", outline="")
        sun = 18 + 34 * self._frame.level
        self._canvas.create_oval(cx - sun, cy - sun, cx + sun, cy + sun, fill="#ffc14d", outline="#fff1a8", width=2)
        for radius, speed, energy, color in (
            (0.20, 0.90, self._frame.bass, BLUE),
            (0.32, -1.25, self._frame.mid, RED),
            (0.44, 0.48, self._frame.treble, GREEN),
        ):
            orbit = min(width, height) * radius
            angle = self._phase * speed
            x = cx + math.cos(angle) * orbit
            y = cy + math.sin(angle) * orbit * 0.55
            planet = 7 + energy * 16
            self._canvas.create_oval(x - planet, y - planet, x + planet, y + planet, fill=color, outline="#ffffff")

    def _draw_freeway(self, width: int, height: int) -> None:
        horizon = height * 0.31
        cx = width / 2
        glow = int(40 + 150 * self._frame.bass)
        for lane in range(-8, 9):
            bottom_x = cx + lane * width * 0.10
            top_x = cx + lane * width * 0.012
            self._canvas.create_line(bottom_x, height, top_x, horizon, fill="#153348", width=1)
        for row in range(12):
            phase = (row / 12.0 + self._phase * 0.04) % 1.0
            y = horizon + (phase**2) * (height - horizon)
            self._canvas.create_line(0, y, width, y, fill="#163244")
        road_half = width * 0.28
        self._canvas.create_polygon(cx, horizon, cx - road_half, height, cx + road_half, height, fill="#071019", outline="#126f9e")
        for offset, color in ((-0.10, BLUE), (0.10, RED)):
            self._canvas.create_line(cx, horizon, cx + width * offset, height, fill=color, width=max(2, glow // 45))

    def _draw_explosion(self, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        if self._frame.bass > 0.63 and len(self._particles) < 260:
            for _ in range(18):
                angle = random.random() * math.tau
                speed = random.uniform(1.8, 7.0) * (0.5 + self._frame.bass)
                self._particles.append([cx, cy, math.cos(angle) * speed, math.sin(angle) * speed, 1.0])
        next_particles: list[list[float]] = []
        for particle in self._particles:
            particle[0] += particle[2]
            particle[1] += particle[3]
            particle[2] *= 0.985
            particle[3] *= 0.985
            particle[4] -= 0.025
            if particle[4] > 0:
                next_particles.append(particle)
                radius = 1 + 4 * particle[4]
                color = RED if particle[4] > 0.55 else "#ffb52c"
                self._canvas.create_oval(particle[0] - radius, particle[1] - radius, particle[0] + radius, particle[1] + radius, fill=color, outline="")
        self._particles = next_particles
        core = 12 + 50 * self._frame.level
        self._canvas.create_oval(cx - core, cy - core, cx + core, cy + core, outline="#fff4a8", width=2 + int(self._frame.level * 6))

    def _draw_stars(self, width: int, height: int) -> None:
        for index, (sx, sy, size) in enumerate(self._stars):
            band = self._frame.spectrum[index % len(self._frame.spectrum)]
            pulse = size + band * 5
            x = (sx * width + math.sin(self._phase + index) * band * 14) % width
            y = (sy * height + math.cos(self._phase * 0.8 + index) * band * 10) % height
            color = self._gradient((index % 24) / 23)
            self._canvas.create_oval(x - pulse, y - pulse, x + pulse, y + pulse, fill=color, outline="")

    def _draw_rings(self, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        maximum = min(width, height) * 0.48
        for index, value in enumerate(self._frame.spectrum[::2]):
            radius = 18 + index * maximum / 13 + value * 18
            color = self._gradient(index / 11)
            self._canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline=color, width=1 + int(value * 5))

    def _draw_ribbon(self, width: int, height: int) -> None:
        points: list[float] = []
        values = self._frame.spectrum
        for index in range(80):
            x = index * width / 79
            band = values[index % len(values)]
            y = height / 2 + math.sin(index * 0.28 + self._phase * 2.1) * height * (0.08 + band * 0.24)
            points.extend((x, y))
        self._canvas.create_line(*points, fill=BLUE, width=8, smooth=True)
        self._canvas.create_line(*points, fill="#75e9ff", width=2, smooth=True)

    def _draw_kaleidoscope(self, width: int, height: int) -> None:
        cx, cy = width / 2, height / 2
        radius = min(width, height) * 0.43
        values = self._frame.spectrum
        spokes = 16
        for spoke in range(spokes):
            angle = math.tau * spoke / spokes + self._phase * 0.18
            value = values[spoke % len(values)]
            inner = radius * (0.12 + value * 0.12)
            outer = radius * (0.50 + value * 0.50)
            x0 = cx + math.cos(angle) * inner
            y0 = cy + math.sin(angle) * inner
            x1 = cx + math.cos(angle + 0.18) * outer
            y1 = cy + math.sin(angle + 0.18) * outer
            x2 = cx + math.cos(angle - 0.18) * outer
            y2 = cy + math.sin(angle - 0.18) * outer
            self._canvas.create_polygon(x0, y0, x1, y1, x2, y2, fill=self._gradient(spoke / spokes), outline="")

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _gradient(position: float) -> str:
        position = max(0.0, min(1.0, position))
        stops = ((22, 139, 209), (132, 206, 31), (241, 90, 22))
        if position < 0.5:
            amount = position * 2.0
            start, end = stops[0], stops[1]
        else:
            amount = (position - 0.5) * 2.0
            start, end = stops[1], stops[2]
        rgb = tuple(round(a + (b - a) * amount) for a, b in zip(start, end))
        return "#" + "".join(f"{channel:02x}" for channel in rgb)


def main() -> None:
    """Standalone visual checkpoint used while the real analysis source is ported."""
    root = tk.Tk()
    root.title("OpenRoadCode Music Visualizer")
    root.geometry("1024x600")
    root.configure(bg=BG)
    panel = MusicVisualizerPanel(root, simulate=True)
    panel.pack(fill=tk.BOTH, expand=True)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
