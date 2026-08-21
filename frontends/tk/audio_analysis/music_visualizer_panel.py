# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Native Tk rendering for OpenRoadCode music analysis."""
from __future__ import annotations

import math
import random
import tkinter as tk
from tkinter import ttk

from controllers.audio_analysis.audio_analysis import AudioAnalysisState


class MusicVisualizerPanel(tk.Frame):
    """Render analyzed audio without coupling the controller to Tk."""

    MODES = ("Spectrum", "Orbiting Planets", "Electric Freeway", "Explosion Field")

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, bg="#0b0d10")
        self._state = AudioAnalysisState(0, 0, 0, 0, 0, ())
        self._phase = 0.0
        self._mode = tk.StringVar(value=self.MODES[0])
        self._stars = [(random.random(), random.random(), random.uniform(.5, 1.5)) for _ in range(55)]
        self._particles: list[tuple[float, float, float]] = []
        self._build()

    def _build(self) -> None:
        controls = tk.Frame(self, bg="#0b0d10")
        controls.pack(fill="x", padx=8, pady=(4, 8))
        tk.Label(controls, text="VISUALIZER", bg="#0b0d10", fg="white", font=("TkDefaultFont", 14, "bold")).pack(side="left")
        combo = ttk.Combobox(controls, textvariable=self._mode, values=self.MODES, state="readonly", width=20)
        combo.pack(side="right")
        self._canvas = tk.Canvas(self, bg="#030509", highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=8)
        meters = tk.Frame(self, bg="#0b0d10")
        meters.pack(fill="x", padx=8, pady=8)
        self._meter_labels: dict[str, tk.Label] = {}
        for name in ("LEVEL", "BASS", "MID", "TREBLE"):
            label = tk.Label(meters, text=f"{name}  0%", bg="#0b0d10", fg="#aebac4", font=("TkDefaultFont", 10, "bold"))
            label.pack(side="left", expand=True)
            self._meter_labels[name.lower()] = label

    def update_state(self, state: AudioAnalysisState) -> None:
        self._state = state
        self._phase += .07 + state.level * .12
        for name in ("level", "bass", "mid", "treble"):
            self._meter_labels[name].configure(text=f"{name.upper()}  {int(getattr(state, name) * 100):02d}%")
        self._draw()

    def _draw(self) -> None:
        c = self._canvas
        c.delete("all")
        w, h = max(2, c.winfo_width()), max(2, c.winfo_height())
        mode = self._mode.get()
        if mode == "Orbiting Planets": self._draw_planets(w, h)
        elif mode == "Electric Freeway": self._draw_freeway(w, h)
        elif mode == "Explosion Field": self._draw_explosion(w, h)
        else: self._draw_spectrum(w, h)

    def _draw_spectrum(self, w: int, h: int) -> None:
        values = self._state.spectrum or (0.0,) * 24
        gap = 3
        bw = max(2, (w - gap * (len(values) + 1)) / len(values))
        for i, value in enumerate(values):
            x0 = gap + i * (bw + gap); y0 = h - 8; y1 = y0 - value * (h - 20)
            hue = i / max(1, len(values) - 1)
            color = self._gradient(hue)
            self._canvas.create_rectangle(x0, y1, x0 + bw, y0, fill=color, outline="")

    def _draw_planets(self, w: int, h: int) -> None:
        cx, cy = w / 2, h / 2
        for sx, sy, size in self._stars:
            glow = int(120 + 135 * self._state.treble)
            color = f"#{glow:02x}{glow:02x}{min(255,glow+20):02x}"
            self._canvas.create_oval(sx*w, sy*h, sx*w+size, sy*h+size, fill=color, outline="")
        sun = 18 + 18 * self._state.level
        self._canvas.create_oval(cx-sun, cy-sun, cx+sun, cy+sun, fill="#ffc24b", outline="#fff1a8", width=2)
        planets = ((.24, .85, self._state.bass, "#55aaff"), (.36, -1.25, self._state.mid, "#ff5d91"), (.46, .42, self._state.treble, "#76ef78"))
        for radius, speed, energy, color in planets:
            rr = min(w, h) * radius
            self._canvas.create_oval(cx-rr, cy-rr*.55, cx+rr, cy+rr*.55, outline="#182936")
            a = self._phase * speed
            px, py = cx + math.cos(a)*rr, cy + math.sin(a)*rr*.55
            pr = 7 + energy*13
            self._canvas.create_oval(px-pr*1.7, py-pr*1.7, px+pr*1.7, py+pr*1.7, fill="", outline=color, width=2)
            self._canvas.create_oval(px-pr, py-pr, px+pr, py+pr, fill=color, outline="white")

    def _draw_freeway(self, w: int, h: int) -> None:
        horizon = h*.28; center = w*.5
        self._canvas.create_polygon(center-w*.08,horizon,center+w*.08,horizon,w*.93,h,w*.07,h,fill="#08141a",outline="#2189b7")
        for lane in (-.5, 0, .5):
            self._canvas.create_line(center+lane*w*.08,horizon,center+lane*w*.62,h,fill="#45c9ff",width=2)
        offset = (self._phase*.12) % 1
        for i in range(9):
            z = (i/9 + offset) % 1
            y = horizon + (z*z)*(h-horizon); spread = z*w*.36
            self._canvas.create_line(center-spread,y,center+spread,y,fill="#174457")
        for i in range(5):
            z = ((i*.19 + self._phase*.018) % 1); y=horizon+z*z*(h-horizon); x=center+(i-2)*w*.07*z
            cw=7+z*20+self._state.bass*8; ch=cw*.45
            color=self._gradient((i*.2+self._phase*.01)%1)
            self._canvas.create_rectangle(x-cw,y-ch,x+cw,y+ch,outline=color,width=2)
            self._canvas.create_oval(x-cw*.7,y,x-cw*.35,y+ch*.7,fill="#ff3c28",outline="")
            self._canvas.create_oval(x+cw*.35,y,x+cw*.7,y+ch*.7,fill="#ff3c28",outline="")

    def _draw_explosion(self, w: int, h: int) -> None:
        cx, cy=w/2,h/2
        if self._state.bass > .68 and len(self._particles) < 90:
            self._particles.extend((random.random()*math.tau, random.uniform(.7,2.4), 0.0) for _ in range(14))
        next_particles=[]
        for angle,speed,age in self._particles:
            age += .025; r=age*min(w,h)*speed
            if age < 1:
                x=cx+math.cos(angle)*r; y=cy+math.sin(angle)*r
                size=max(1,5*(1-age)); color="#fff09a" if age<.35 else "#ff642f"
                self._canvas.create_oval(x-size,y-size,x+size,y+size,fill=color,outline="")
                next_particles.append((angle,speed,age))
        self._particles=next_particles
        pulse=18+self._state.bass*55
        self._canvas.create_oval(cx-pulse*1.6,cy-pulse*1.6,cx+pulse*1.6,cy+pulse*1.6,outline="#ff3b19",width=3)
        self._canvas.create_oval(cx-pulse,cy-pulse,cx+pulse,cy+pulse,fill="#ffb02e",outline="#fff4b0",width=2)

    @staticmethod
    def _gradient(x: float) -> str:
        x %= 1.0
        r=int(128+127*math.sin(math.tau*(x+.00)));g=int(128+127*math.sin(math.tau*(x+.33)));b=int(128+127*math.sin(math.tau*(x+.66)))
        return f"#{r:02x}{g:02x}{b:02x}"
