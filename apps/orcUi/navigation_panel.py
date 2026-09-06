# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full navigation panel for the integrated ORC cockpit UI."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from ui.navigation import MapRequestHandlerIf
from ui.theme import ThemeBundle, ThemeMode


class NavigationPanel(tk.Frame):
    """Map host and navigation controls styled from the active ORC theme."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        map_request_handler: MapRequestHandlerIf | None = None,
        on_back: Callable[[], None] | None = None,
        theme_bundle: ThemeBundle | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle or packaged_theme_bundle(ThemeMode.DARK)
        super().__init__(parent, bg=self._theme_bundle.ui.background)
        del on_back

        runtime = get_shared_map_camera_runtime()
        self._request_handler = map_request_handler or runtime.request_handler
        self._zoom_level = float(getattr(self._request_handler, "zoom_level", 16.5))
        self._pitch_rad = float(
            getattr(self._request_handler, "pitch_rad", math.radians(45.0))
        )
        self._follow_enabled = bool(
            getattr(self._request_handler, "follow_enabled", True)
        )
        self._poi_focus = set(getattr(self._request_handler, "poi_focus", ()))
        self._shortcut_status = tk.StringVar(value=self._focus_status())
        self._map_host: tk.Frame
        self._follow_button: tk.Button
        self._build()
        self._schedule_renderer_refresh()

    @property
    def map_host_window_id(self) -> int:
        self.update_idletasks()
        return self._map_host.winfo_id()

    def set_theme_bundle(self, theme_bundle: ThemeBundle) -> None:
        """Rebuild navigation chrome using a CSS-derived theme bundle."""
        self._theme_bundle = theme_bundle
        self.configure(bg=theme_bundle.ui.background)
        for child in self.winfo_children():
            child.destroy()
        self._build()

    def set_map_request_handler(self, handler: MapRequestHandlerIf | None) -> None:
        if handler is not None:
            self._request_handler = handler

    def set_follow_enabled(self, enabled: bool) -> None:
        self._follow_enabled = enabled
        ui = self._theme_bundle.ui
        self._follow_button.configure(
            text="F" if enabled else "F̸",
            fg=ui.accent_success if enabled else ui.text,
        )

    def _build(self) -> None:
        ui = self._theme_bundle.ui
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        bar = tk.Frame(
            self,
            bg=ui.surface_alt,
            height=38,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        bar.grid_propagate(False)

        shortcuts = tk.Frame(bar, bg=ui.surface_alt)
        shortcuts.pack(side=tk.LEFT, padx=4, pady=3)
        shortcut_specs = (
            ("⌂ HOME", ui.accent_primary, "home"),
            ("▣ WORK", ui.accent_warning, "work"),
            ("⛽ GAS", ui.accent_danger, "gas"),
            ("▣ GROCERY", ui.accent_success, "grocery"),
            ("♨ FOOD", ui.accent_danger, "food"),
        )
        for label, accent, key in shortcut_specs:
            tk.Button(
                shortcuts,
                text=label,
                command=lambda selected=key: self._destination_shortcut(selected),
                bg=ui.control_background,
                fg=accent,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=ui.border,
                font=("Sans", 8, "bold"),
                width=9,
                height=1,
                padx=3,
                pady=1,
            ).pack(side=tk.LEFT, padx=(0, 4))

        tk.Label(
            bar,
            textvariable=self._shortcut_status,
            bg=ui.surface_alt,
            fg=ui.text_muted,
            font=("Sans", 7),
            anchor="e",
        ).pack(side=tk.RIGHT, padx=7)

        body = tk.Frame(self, bg=ui.background)
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self._map_host = tk.Frame(
            body,
            bg=ui.background,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        self._map_host.grid(row=0, column=0, sticky="nsew")

        controls = tk.Frame(
            body,
            bg=ui.surface_alt,
            width=62,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        controls.grid(row=0, column=1, sticky="ns", padx=(4, 0))
        controls.grid_propagate(False)

        self._follow_button = self._control(
            controls,
            "F",
            self._toggle_follow,
            ui.accent_success,
        )
        self._follow_button.pack(fill=tk.X, padx=5, pady=(7, 5))
        self.set_follow_enabled(self._follow_enabled)

        pan = tk.Frame(controls, bg=ui.surface_alt)
        pan.pack(pady=2)
        for row, column, label, up, right in (
            (0, 1, "▲", 1, 0),
            (1, 0, "◀", 0, -1),
            (1, 2, "▶", 0, 1),
            (2, 1, "▼", -1, 0),
        ):
            tk.Button(
                pan,
                text=label,
                command=lambda u=up, r=right: self._pan(u, r),
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=ui.border,
                font=("Sans", 9, "bold"),
                width=1,
                height=1,
                padx=2,
                pady=1,
            ).grid(row=row, column=column, padx=1, pady=1)

        for label, command, accent in (
            ("+", lambda: self._change_zoom(1), ui.accent_primary),
            ("−", lambda: self._change_zoom(-1), ui.accent_primary),
            ("↗", lambda: self._change_pitch(5), ui.accent_warning),
            ("↘", lambda: self._change_pitch(-5), ui.accent_warning),
            ("N", self._north_up, ui.text),
            ("◎", self._recenter, ui.accent_success),
        ):
            self._control(controls, label, command, accent).pack(
                fill=tk.X,
                padx=5,
                pady=2,
            )

        tk.Label(
            controls,
            text="ZOOM\nTILT\nNORTH\nCENTER",
            bg=ui.surface_alt,
            fg=ui.text_muted,
            font=("Sans", 6),
            justify=tk.CENTER,
        ).pack(side=tk.BOTTOM, pady=5)

    def _control(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], None],
        foreground: str,
    ) -> tk.Button:
        ui = self._theme_bundle.ui
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=ui.control_background,
            fg=foreground,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", 11, "bold"),
            height=1,
        )

    def _schedule_renderer_refresh(self) -> None:
        for delay_ms in (300, 700, 1200):
            self.after(delay_ms, self._refresh_renderer_state)

    def _refresh_renderer_state(self) -> None:
        refresh = getattr(self._request_handler, "refresh_renderer_state", None)
        if refresh is not None:
            refresh()

    def _focus_status(self) -> str:
        names: list[str] = []
        if "fuel" in self._poi_focus:
            names.append("Gas")
        if "grocery" in self._poi_focus:
            names.append("Grocery")
        return " + ".join(names) + " highlighted" if names else ""

    def _destination_shortcut(self, shortcut: str) -> None:
        focus_category = {"gas": "fuel", "grocery": "grocery"}.get(shortcut)
        if focus_category is not None:
            if focus_category in self._poi_focus:
                self._poi_focus.remove(focus_category)
            else:
                self._poi_focus.add(focus_category)
            self._request_handler.request_poi_focus(focus_category)
            self._shortcut_status.set(self._focus_status())
            return

        self._request_handler.request_poi_focus(None)
        self._poi_focus.clear()
        messages = {
            "home": "Home location not configured",
            "work": "Work location not configured",
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
        self._request_handler.request_pan_screen(
            right_px=right * max(48, self._map_host.winfo_width() * 0.25),
            up_px=up * max(48, self._map_host.winfo_height() * 0.25),
        )

    def _change_zoom(self, delta: float) -> None:
        self._zoom_level = max(1, min(22, self._zoom_level + delta))
        self.set_follow_enabled(False)
        self._request_handler.request_zoom(self._zoom_level)

    def _change_pitch(self, delta_deg: float) -> None:
        pitch_deg = max(
            0,
            min(60, math.degrees(self._pitch_rad) + delta_deg),
        )
        self._pitch_rad = math.radians(pitch_deg)
        self.set_follow_enabled(False)
        self._request_handler.request_pitch(self._pitch_rad)

    def _north_up(self) -> None:
        self.set_follow_enabled(False)
        self._request_handler.request_bearing(0.0)

    def _recenter(self) -> None:
        self.set_follow_enabled(True)
        self._request_handler.request_recenter()
