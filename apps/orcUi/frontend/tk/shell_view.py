# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent chrome ownership for the integrated orcUi Tk shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from datetime import datetime

from apps.orcUi.orc_theme import ThemeMode, toggle_label
from ui.theme import ThemeBundle
from ui.weather import WeatherAlertUiEvent

from .bottom_bar import OrcUiBottomBar
from .shell_chrome import build_footer, build_top_bar
from .shell_metrics import SHELL_PAD_X, SHELL_PAD_Y
from .side_nav import OrcUiSideNav
from .weather_alert_banner import WeatherAlertBanner


class OrcUiShellView:
    """Own persistent shell widgets while preserving the central content host."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        theme: ThemeBundle,
        theme_mode: ThemeMode,
        nav_items: list[str],
        active_nav: str,
        on_navigate: Callable[[str], None],
        on_power: Callable[[], None],
        on_theme_toggle: Callable[[], None],
        on_volume_down: Callable[[], None],
        on_volume_up: Callable[[], None],
        volume_text: str,
    ) -> None:
        self._root = root
        self._theme = theme
        self._theme_mode = theme_mode
        self._nav_items = nav_items
        self._active_nav = active_nav
        self._on_navigate = on_navigate
        self._on_power = on_power
        self._on_theme_toggle = on_theme_toggle
        self._on_volume_down = on_volume_down
        self._on_volume_up = on_volume_up
        self._volume_text = volume_text
        self._adsb_enabled = False
        self._aircraft_count = 0
        self._adsb_toggle_handler: Callable[[bool], bool] | None = None
        self._adsb_view_handler: Callable[[], None] | None = None
        self._side_nav: OrcUiSideNav | None = None
        self._bottom_bar: OrcUiBottomBar | None = None
        self._clock_label: tk.Label | None = None
        self._breadcrumb_label: tk.Label | None = None
        self._breadcrumb = active_nav
        self._clock_after_id: str | None = None
        self._weather_alert: WeatherAlertUiEvent | None = None
        self._weather_alert_banner: WeatherAlertBanner | None = None
        self._weather_alert_after_id: str | None = None

        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(1, weight=1)
        self.content = tk.Frame(root, bg=theme.ui.background)
        self.content.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(SHELL_PAD_Y, SHELL_PAD_X),
            pady=SHELL_PAD_Y,
        )
        self._build_chrome()
        self._update_clock()

    def rebuild(self, *, theme: ThemeBundle, theme_mode: ThemeMode) -> None:
        self._theme = theme
        self._theme_mode = theme_mode
        for child in self._root.winfo_children():
            if child is self.content:
                continue
            child.destroy()
        self._root.configure(bg=theme.ui.background)
        self.content.configure(bg=theme.ui.background)
        self._build_chrome()
        if self._weather_alert is not None:
            self.show_weather_alert(self._weather_alert)

    def rebuild_navigation(self) -> None:
        if self._side_nav is not None and self._side_nav.winfo_exists():
            self._side_nav.rebuild(
                theme=self._theme,
                items=self._nav_items,
                active=self._active_nav,
            )

    def set_active_navigation(self, name: str) -> None:
        self._active_nav = name
        self.set_breadcrumb(name)
        if self._side_nav is not None and self._side_nav.winfo_exists():
            self._side_nav.set_active(active=name, theme=self._theme)

    def set_breadcrumb(self, *parts: str) -> None:
        normalized = [part.strip().upper() for part in parts if part and part.strip()]
        deduplicated = [
            part for index, part in enumerate(normalized)
            if index == 0 or part != normalized[index - 1]
        ]
        self._breadcrumb = "  ›  ".join(deduplicated) if deduplicated else self._active_nav
        if self._breadcrumb_label is not None and self._breadcrumb_label.winfo_exists():
            self._breadcrumb_label.configure(text=self._breadcrumb)

    def close(self) -> None:
        self._cancel_weather_alert_timer()
        if self._clock_after_id is not None:
            try:
                self._root.after_cancel(self._clock_after_id)
            except tk.TclError:
                pass
            self._clock_after_id = None

    def set_volume_text(self, text: str) -> None:
        self._volume_text = text
        if self._bottom_bar is not None and self._bottom_bar.winfo_exists():
            self._bottom_bar.set_volume_text(text)

    def set_adsb_handlers(
        self,
        *,
        on_toggle: Callable[[bool], bool],
        on_view: Callable[[], None],
    ) -> None:
        self._adsb_toggle_handler = on_toggle
        self._adsb_view_handler = on_view
        if self._bottom_bar is not None and self._bottom_bar.winfo_exists():
            self._bottom_bar.set_adsb_handlers(on_toggle=on_toggle, on_view=on_view)

    def set_adsb_state(self, *, enabled: bool, aircraft_count: int) -> None:
        self._adsb_enabled = bool(enabled)
        self._aircraft_count = max(0, int(aircraft_count))
        if self._bottom_bar is not None and self._bottom_bar.winfo_exists():
            self._bottom_bar.set_adsb_state(
                enabled=self._adsb_enabled,
                aircraft_count=self._aircraft_count,
            )

    def show_weather_alert(self, alert: WeatherAlertUiEvent) -> None:
        """Show or replace the shell-level weather alert overlay."""
        self._weather_alert = alert
        banner = self._weather_alert_banner
        if banner is None or not banner.winfo_exists():
            banner = WeatherAlertBanner(
                self._root,
                theme=self._theme,
                on_details=self._show_weather_alert_details,
                on_dismiss=self.dismiss_weather_alert,
            )
            self._weather_alert_banner = banner
        banner.set_alert(alert)
        banner.place(relx=0.5, y=52, anchor="n", relwidth=0.78)
        banner.lift()
        self._schedule_weather_alert_tick()

    def _schedule_weather_alert_tick(self) -> None:
        self._cancel_weather_alert_timer()
        alert = self._weather_alert
        if alert is None:
            return
        now = datetime.now().astimezone()
        if alert.expires_at is not None and alert.expires_at <= now:
            self.dismiss_weather_alert()
            return
        banner = self._weather_alert_banner
        if banner is not None and banner.winfo_exists():
            banner.update_expiration(now)
        self._weather_alert_after_id = self._root.after(1000, self._schedule_weather_alert_tick)

    def _cancel_weather_alert_timer(self) -> None:
        if self._weather_alert_after_id is None:
            return
        try:
            self._root.after_cancel(self._weather_alert_after_id)
        except tk.TclError:
            pass
        self._weather_alert_after_id = None

    def dismiss_weather_alert(self) -> None:
        """Dismiss the currently visible weather alert from this shell."""
        self._cancel_weather_alert_timer()
        self._weather_alert = None
        banner = self._weather_alert_banner
        if banner is not None and banner.winfo_exists():
            banner.place_forget()

    def _show_weather_alert_details(self) -> None:
        alert = self._weather_alert
        if alert is None:
            return
        detail = tk.Toplevel(self._root)
        detail.title(alert.event)
        detail.transient(self._root)
        detail.configure(bg=self._theme.ui.background)
        detail.geometry("720x420")
        ui = self._theme.ui
        tk.Label(
            detail,
            text=alert.event.upper(),
            bg=ui.background,
            fg=ui.accent_danger if alert.severity.lower() in {"extreme", "severe"} else ui.text,
            font=("Sans", 18, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=18, pady=(16, 6))
        tk.Label(
            detail,
            text=alert.headline,
            bg=ui.background,
            fg=ui.text,
            font=("Sans", 12, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=680,
        ).pack(fill=tk.X, padx=18, pady=(0, 12))
        body = alert.description
        if alert.instruction:
            body = f"{body}\n\n{alert.instruction}"
        tk.Label(
            detail,
            text=body,
            bg=ui.background,
            fg=ui.text_muted,
            font=("Sans", 11),
            anchor="nw",
            justify=tk.LEFT,
            wraplength=680,
        ).pack(fill=tk.BOTH, expand=True, padx=18, pady=(0, 12))
        tk.Button(
            detail,
            text="CLOSE",
            command=detail.destroy,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground=ui.text,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
        ).pack(pady=(0, 16))

    def _update_clock(self) -> None:
        if not self._root.winfo_exists():
            return
        text = datetime.now().strftime("%I:%M %p     %a, %b %d").lstrip("0")
        if self._clock_label is not None and self._clock_label.winfo_exists():
            self._clock_label.configure(text=text)
        self._clock_after_id = self._root.after(1000, self._update_clock)

    def _build_chrome(self) -> None:
        self._weather_alert_banner = None
        self._clock_label = build_top_bar(
            self._root,
            theme=self._theme,
            on_power=self._on_power,
        )
        self._side_nav = OrcUiSideNav(
            self._root,
            theme=self._theme,
            items=self._nav_items,
            active=self._active_nav,
            on_navigate=self._on_navigate,
        )
        self._side_nav.grid(
            row=1,
            column=0,
            sticky="ns",
            padx=(SHELL_PAD_X, 0),
            pady=SHELL_PAD_Y,
        )
        self._side_nav.grid_propagate(False)

        self._bottom_bar = OrcUiBottomBar(
            self._root,
            theme=self._theme,
            volume_text=self._volume_text,
            theme_label=toggle_label(self._theme_mode),
            on_volume_down=self._on_volume_down,
            on_volume_up=self._on_volume_up,
            on_settings=lambda: self._on_navigate("SETTINGS"),
            on_theme_toggle=self._on_theme_toggle,
        )
        self._bottom_bar.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=SHELL_PAD_X,
        )
        if self._adsb_toggle_handler is not None and self._adsb_view_handler is not None:
            self._bottom_bar.set_adsb_handlers(
                on_toggle=self._adsb_toggle_handler,
                on_view=self._adsb_view_handler,
            )
        self._bottom_bar.set_adsb_state(
            enabled=self._adsb_enabled,
            aircraft_count=self._aircraft_count,
        )
        self._breadcrumb_label, _status_label = build_footer(self._root, theme=self._theme)
        self._breadcrumb_label.configure(text=self._breadcrumb)
