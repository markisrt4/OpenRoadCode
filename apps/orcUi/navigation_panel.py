# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full navigation panel for the integrated ORC cockpit UI."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from apps.launchers.android_intent_launcher import (
    AndroidIntentLauncher,
    AndroidIntentLauncherError,
)
from apps.orcUi.shared_map_camera import get_shared_map_camera_runtime
from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from controllers.poi import (
    PoiAction,
    PoiActionKind,
    PoiCategory,
    PoiSearchController,
    PointOfInterest,
)
from ui.navigation import MapRequestHandlerIf
from ui.theme import ThemeBundle, ThemeMode


_POI_SEARCH_SETTLE_MS = 750


class NavigationPanel(tk.Frame):
    """Map host, navigation controls, and nearby POI discovery."""

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
        self._android_launcher = AndroidIntentLauncher()
        self._poi_controller = PoiSearchController()
        self._poi_card: tk.Frame | None = None
        self._poi_search_after_id: str | None = None
        self._zoom_level = float(getattr(self._request_handler, "zoom_level", 16.5))
        self._pitch_rad = float(
            getattr(self._request_handler, "pitch_rad", math.radians(45.0))
        )
        self._follow_enabled = bool(
            getattr(self._request_handler, "follow_enabled", True)
        )
        self._shortcut_status = tk.StringVar(value="")
        self._map_host: tk.Frame
        self._follow_button: tk.Button
        self._build()
        self._schedule_renderer_refresh()
        self.after(100, self._poll_poi_events)

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
        self._poi_card = None
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

    def destroy(self) -> None:
        if self._poi_search_after_id is not None:
            try:
                self.after_cancel(self._poi_search_after_id)
            except tk.TclError:
                pass
            self._poi_search_after_id = None
        self._poi_controller.close()
        super().destroy()

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
            ("▰ TRANSIT", ui.accent_primary, "transit"),
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

    def _destination_shortcut(self, shortcut: str) -> None:
        category = {
            "food": PoiCategory.FOOD,
            "gas": PoiCategory.FUEL,
            "grocery": PoiCategory.GROCERY,
            "transit": PoiCategory.TRANSIT,
        }.get(shortcut)
        if category is not None:
            self._start_poi_search(category)
            return

        self._poi_controller.clear()
        self._request_handler.request_poi_focus(None)
        messages = {
            "home": "Home location not configured",
            "work": "Work location not configured",
        }
        self._shortcut_status.set(messages[shortcut])
        self.after(2500, lambda: self._shortcut_status.set(""))

    def _start_poi_search(self, category: PoiCategory) -> None:
        if not bool(getattr(self._request_handler, "camera_initialized", False)):
            self._shortcut_status.set(
                "Position unavailable — nearby search needs a GPS fix"
            )
            return

        if self._poi_search_after_id is not None:
            try:
                self.after_cancel(self._poi_search_after_id)
            except tk.TclError:
                pass
            self._poi_search_after_id = None

        category_name = category.name.casefold()
        self._poi_controller.clear()
        self.set_follow_enabled(False)
        self._request_handler.request_follow(False)
        self._request_handler.request_poi_focus(None)
        self._request_handler.request_poi_focus(category_name)
        self._zoom_level = max(self._zoom_level, 14.0)
        self._shortcut_status.set(f"Loading nearby {category_name}…")
        self._poi_search_after_id = self.after(
            _POI_SEARCH_SETTLE_MS,
            lambda: self._issue_poi_search(category),
        )

    def _issue_poi_search(self, category: PoiCategory) -> None:
        self._poi_search_after_id = None
        self._shortcut_status.set(f"Searching nearby {category.name.casefold()}…")
        self._poi_controller.search(category)

    def _poll_poi_events(self) -> None:
        result = self._poi_controller.poll_search_result()
        if result is not None:
            if result.count > 0:
                noun = result.category.name.casefold()
                suffix = "s" if result.count != 1 else ""
                self._shortcut_status.set(
                    f"{result.count} {noun} result{suffix}"
                )
            else:
                self._shortcut_status.set(
                    f"No {result.category.name.casefold()} results nearby"
                )

        poi = self._poi_controller.poll_selected()
        if poi is not None:
            self._show_poi_card(poi)

        if self.winfo_exists():
            self.after(100, self._poll_poi_events)

    def _show_poi_card(self, poi: PointOfInterest) -> None:
        ui = self._theme_bundle.ui
        if self._poi_card is not None and self._poi_card.winfo_exists():
            self._poi_card.destroy()

        card = tk.Frame(
            self,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.accent_primary,
        )
        card.place(relx=0.5, rely=0.78, anchor=tk.CENTER, width=390, height=112)
        self._poi_card = card

        tk.Label(
            card,
            text=poi.name,
            bg=ui.surface_alt,
            fg=ui.text,
            font=("Sans", 12, "bold"),
        ).pack(pady=(10, 5))

        buttons = tk.Frame(card, bg=ui.surface_alt)
        buttons.pack()
        for action in poi.actions:
            if action.kind is PoiActionKind.OPEN_URI and action.uri:
                tk.Button(
                    buttons,
                    text=action.label,
                    command=lambda selected=action: self._execute_poi_action(selected),
                    bg=ui.control_background,
                    fg=ui.accent_primary,
                    activebackground=ui.control_active,
                    activeforeground="#ffffff",
                    relief=tk.FLAT,
                    highlightthickness=1,
                    highlightbackground=ui.border,
                    font=("Sans", 10, "bold"),
                    width=12,
                    height=2,
                ).pack(side=tk.LEFT, padx=4)

        tk.Button(
            buttons,
            text="CLOSE",
            command=card.destroy,
            bg=ui.control_background,
            fg=ui.text_muted,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", 8, "bold"),
            width=8,
        ).pack(side=tk.LEFT, padx=4)

    def _execute_poi_action(self, action: PoiAction) -> None:
        if action.kind is PoiActionKind.OPEN_URI and action.uri:
            try:
                self._android_launcher.open_uri(action.uri)
                self._shortcut_status.set(f"Opening {action.label.casefold()}")
            except AndroidIntentLauncherError as exc:
                self._shortcut_status.set(f"Launch failed: {exc}")

        if self._poi_card is not None and self._poi_card.winfo_exists():
            self._poi_card.destroy()
        self.after(3500, lambda: self._shortcut_status.set(""))

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
