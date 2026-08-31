# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full navigation panel for the integrated ORC cockpit UI."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.map_camera_runtime import MapCameraRuntime
from ui.navigation import MapRequestHandlerIf

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
RED = "#f15a16"
PURPLE = "#a25ce5"


class NavigationPanel(tk.Frame):
    """Provide the navigation map host and renderer-neutral camera controls."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        del on_back
        self._zoom_level = 16.5
        self._pitch_rad = math.radians(45.0)
        self._follow_enabled = True
        self._follow_button: tk.Button
        self._map_host: tk.Frame
        self._shortcut_status: tk.StringVar
        self._camera_runtime = MapCameraRuntime(
            zoom_level=self._zoom_level,
            pitch_rad=self._pitch_rad,
            follow_enabled=True,
        )
        self._request_handler = self._camera_runtime.request_handler
        self._build()
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._camera_runtime.start()

    @property
    def map_host_window_id(self) -> int:
        self.update_idletasks()
        return self._map_host.winfo_id()

    def set_map_request_handler(self, handler: MapRequestHandlerIf | None) -> None:
        if handler is not None:
            self._request_handler = handler

    def set_follow_enabled(self, enabled: bool) -> None:
        self._follow_enabled = enabled
        self._follow_button.configure(
            text="FOLLOW  ON" if enabled else "FOLLOW  OFF",
            fg=GREEN if enabled else TEXT,
        )

    def _build(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self, bg=BG, height=68)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)

        title_row = tk.Frame(header, bg=BG)
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)
        tk.Label(
            title_row,
            text="NAVIGATION",
            bg=BG,
            fg=TEXT,
            font=("Sans", 13, "bold"),
        ).grid(row=0, column=0)

        shortcuts = tk.Frame(header, bg=BG)
        shortcuts.grid(row=1, column=0, sticky="ew", padx=2, pady=(3, 0))
        for column in range(4):
            shortcuts.grid_columnconfigure(column, weight=1, uniform="nav-shortcut")

        for column, text, accent, key in (
            (0, "⌂  HOME", BLUE, "home"),
            (1, "▣  WORK", PURPLE, "work"),
            (2, "⛽  GAS", GREEN, "gas"),
            (3, "✦  FOOD", RED, "food"),
        ):
            tk.Button(
                shortcuts,
                text=text,
                command=lambda shortcut=key: self._destination_shortcut(shortcut),
                bg=PANEL,
                fg=accent,
                activebackground="#101820",
                activeforeground=TEXT,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=BORDER,
                font=("Sans", 9, "bold"),
                height=1,
            ).grid(row=0, column=column, sticky="ew", padx=2)

        self._shortcut_status = tk.StringVar(value="")
        tk.Label(
            header,
            textvariable=self._shortcut_status,
            bg=BG,
            fg=MUTED,
            font=("Sans", 7),
            anchor="e",
        ).place(relx=0.995, rely=0.02, anchor="ne")

        body = tk.Frame(self, bg=BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        self._map_host = tk.Frame(body, bg="#020406", highlightthickness=1, highlightbackground=BORDER)
        self._map_host.grid(row=0, column=0, sticky="nsew")

        controls = tk.Frame(body, bg=PANEL, width=142)
        controls.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        controls.grid_propagate(False)
        self._follow_button = tk.Button(
            controls, text="FOLLOW  ON", command=self._toggle_follow,
            bg=PANEL, fg=GREEN, activebackground="#101820", activeforeground=GREEN,
            relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER,
            font=("Sans", 9, "bold"), height=2,
        )
        self._follow_button.pack(fill=tk.X, padx=6, pady=(8, 5))

        tk.Label(controls, text="PAN MAP", bg=PANEL, fg=BLUE, font=("Sans", 8, "bold")).pack(pady=(3, 0))
        pan = tk.Frame(controls, bg=PANEL)
        pan.pack(padx=6, pady=4)
        for row, column, text, up, right in (
            (0, 1, "▲", 1.0, 0.0),
            (1, 0, "◀", 0.0, -1.0),
            (1, 2, "▶", 0.0, 1.0),
            (2, 1, "▼", -1.0, 0.0),
        ):
            tk.Button(
                pan, text=text, command=lambda u=up, r=right: self._pan(u, r),
                bg="#101820", fg=TEXT, activebackground=BLUE, activeforeground=TEXT,
                relief=tk.FLAT, highlightthickness=1, highlightbackground="#3d5362",
                font=("Sans", 13, "bold"), width=3, height=1,
            ).grid(row=row, column=column, padx=2, pady=2)

        for text, command in (
            ("ZOOM +", lambda: self._change_zoom(1.0)),
            ("ZOOM −", lambda: self._change_zoom(-1.0)),
            ("TILT +", lambda: self._change_pitch(5.0)),
            ("TILT −", lambda: self._change_pitch(-5.0)),
            ("NORTH UP", self._north_up),
            ("RECENTER", self._recenter),
        ):
            tk.Button(
                controls, text=text, command=command, bg=PANEL, fg=TEXT,
                activebackground="#101820", activeforeground=GREEN, relief=tk.FLAT,
                highlightthickness=1, highlightbackground=BORDER,
                font=("Sans", 9, "bold"), height=1,
            ).pack(fill=tk.X, padx=6, pady=3)

        tk.Label(
            controls, text="Pan / zoom / tilt\nturn FOLLOW off",
            bg=PANEL, fg=MUTED, font=("Sans", 8), justify=tk.CENTER,
        ).pack(side=tk.BOTTOM, pady=8)

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is self:
            self._camera_runtime.close()

    def _destination_shortcut(self, shortcut: str) -> None:
        messages = {
            "home": "Home location not configured",
            "work": "Work location not configured",
            "gas": "Nearby gas search not connected yet",
            "food": "Nearby food search not connected yet",
        }
        self._shortcut_status.set(messages[shortcut])
        self.after(2500, lambda: self._shortcut_status.set(""))

    def _toggle_follow(self) -> None:
        enabled = not self._follow_enabled
        self.set_follow_enabled(enabled)
        self._request_handler.request_follow(enabled)

    def _pan(self, up: float, right: float) -> None:
        self.set_follow_enabled(False)
        self._map_host.update_idletasks()
        horizontal_px = max(48.0, self._map_host.winfo_width() * 0.25)
        vertical_px = max(48.0, self._map_host.winfo_height() * 0.25)
        self._request_handler.request_pan_screen(
            right_px=right * horizontal_px,
            up_px=up * vertical_px,
        )

    def _change_zoom(self, delta: float) -> None:
        self._zoom_level = max(1.0, min(22.0, self._zoom_level + delta))
        self.set_follow_enabled(False)
        self._request_handler.request_zoom(self._zoom_level)

    def _change_pitch(self, delta_deg: float) -> None:
        pitch_deg = max(0.0, min(60.0, math.degrees(self._pitch_rad) + delta_deg))
        self._pitch_rad = math.radians(pitch_deg)
        self.set_follow_enabled(False)
        self._request_handler.request_pitch(self._pitch_rad)

    def _north_up(self) -> None:
        self.set_follow_enabled(False)
        self._request_handler.request_bearing(0.0)

    def _recenter(self) -> None:
        self.set_follow_enabled(True)
        self._request_handler.request_recenter()
