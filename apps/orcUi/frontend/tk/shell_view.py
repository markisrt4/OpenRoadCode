# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Persistent chrome ownership for the integrated orcUi Tk shell."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.orc_theme import ThemeMode, toggle_label
from ui.theme import ThemeBundle

from .bottom_bar import OrcUiBottomBar
from .shell_chrome import build_footer, build_top_bar
from .shell_metrics import SHELL_PAD_X, SHELL_PAD_Y
from .side_nav import OrcUiSideNav


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

    def rebuild_navigation(self) -> None:
        if self._side_nav is not None and self._side_nav.winfo_exists():
            self._side_nav.rebuild(
                theme=self._theme,
                items=self._nav_items,
                active=self._active_nav,
            )

    def set_active_navigation(self, name: str) -> None:
        self._active_nav = name
        if self._side_nav is not None and self._side_nav.winfo_exists():
            self._side_nav.set_active(active=name, theme=self._theme)

    def set_clock_text(self, text: str) -> None:
        if self._clock_label is not None and self._clock_label.winfo_exists():
            self._clock_label.configure(text=text)

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

    def _build_chrome(self) -> None:
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
            pady=(0, SHELL_PAD_Y),
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
        build_footer(self._root, theme=self._theme)
