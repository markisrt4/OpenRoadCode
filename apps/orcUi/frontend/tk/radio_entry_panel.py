# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level radio chooser and SDR++ presentation handoff for orcUi."""

from __future__ import annotations

import tkinter as tk
from functools import partial
from collections.abc import Callable

from ui.system.online_mode_if import OnlineModeIf
from frontends.tk.offline_card import OfflineCardAppearance
from apps.orcUi.frontend.tk.radio_panel import RadioPanel
from frontends.tk.radio.persistent_streaming_radio_panel import PersistentStreamingRadioPanel
from ui.theme import ThemeBundle
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL
from .radio_source_icon import draw_source_icon
from ui.ui_widget import UiWidget


class RadioEntryPanel(tk.Frame, UiWidget):
    """Offer RF or streaming radio and host the active radio presentation."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        rf_panel_factory: Callable[[tk.Misc, ThemeBundle], RadioPanel],
        streaming_panel_factory: Callable[
            [tk.Misc, ThemeBundle, Callable[[], None]], PersistentStreamingRadioPanel
        ],
        theme: ThemeBundle,
        on_location_changed: Callable[[str], None] | None = None,
        online_mode: OnlineModeIf | None = None,
    ) -> None:
        self._online_mode = online_mode
        self._unsubscribe_online = (online_mode.subscribe(self._mode_changed)
                                    if online_mode is not None else lambda: None)
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._rf_panel_factory = rf_panel_factory
        self._streaming_panel_factory = streaming_panel_factory
        self._radio_panel: RadioPanel | None = None
        self._streaming_page: PersistentStreamingRadioPanel | None = None
        self._on_location_changed = on_location_changed

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._chooser = tk.Frame(self, bg=ui.background)
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._chooser.grid_columnconfigure(0, weight=1, uniform="radio-source")
        self._chooser.grid_columnconfigure(1, weight=1, uniform="radio-source")
        self._chooser.grid_rowconfigure(0, weight=1)
        self._build_choice_buttons()

    def _online_allowed(self) -> bool:
        mode = getattr(self, "_online_mode", None)
        return mode is None or mode.online

    def _mode_changed(self, online: bool) -> None:
        self._streaming_card_appearance.set_online(online)
        self._streaming_button.configure(state=tk.NORMAL if online else tk.DISABLED,
                                         disabledforeground=self._theme.ui.text_muted)
        if not online:
            if self._streaming_page is not None and self._streaming_page.winfo_exists():
                self._streaming_page.destroy()
                self._streaming_page = None
                self._show_chooser()
            self._status.configure(text="Offline mode: RF radio remains available")

    def deactivate(self) -> None:
        """Retire browser callbacks as the containing radio screen is hidden."""
        if self._streaming_page is not None:
            self._streaming_page.deactivate()
        if self._radio_panel is not None:
            self._radio_panel.deactivate()

    def destroy(self) -> None:
        self._unsubscribe_online()
        super().destroy()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply a live ORC theme without restarting radio playback."""
        self._theme = theme
        self.configure(bg=theme.ui.background)
        self._chooser.configure(bg=theme.ui.background)
        for child in self._chooser.winfo_children():
            child.destroy()
        self._build_choice_buttons()
        if self._streaming_page is not None and self._streaming_page.winfo_exists():
            self._streaming_page.set_theme_bundle(theme)
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.set_theme_bundle(theme)

    def open_streaming_radio(self) -> None:
        """Present the streaming-radio browser directly."""
        if not self._online_allowed():
            self._status.configure(text="Offline mode: internet radio unavailable")
            return
        self._show_streaming_radio()
        self._set_location("STREAMING")

    def open_rf_radio(self) -> None:
        """Launch and present the RF radio directly."""
        self._launch_rf_radio()
        self._set_location("RF")

    def open_adsb(self) -> None:
        """Present the ADS-B aircraft dashboard without starting SDR++ first."""
        self._chooser.grid_remove()
        if self._streaming_page is not None and self._streaming_page.winfo_exists():
            self._streaming_page.deactivate()
            self._streaming_page.grid_remove()
        if self._radio_panel is None or not self._radio_panel.winfo_exists():
            self._radio_panel = self._rf_panel_factory(self, self._theme)
        self._radio_panel.grid(row=0, column=0, sticky="nsew")
        self._radio_panel.show_adsb()
        self._set_location("AIRCRAFT")

    def _build_choice_buttons(self) -> None:
        ui = self._theme.ui
        rf_card, self._rf_button = self._build_source_card(
            parent=self._chooser,
            title="RF RADIO",
            eyebrow="SOFTWARE DEFINED RADIO",
            description="Tune live RF with SDR++ spectrum and waterfall controls.",
            features="FM  •  WEATHER  •  AIRBAND  •  HAM",
            action_text="OPEN RF RADIO  ›",
            accent=ui.accent_success,
            icon_kind="rf",
            command=self.open_rf_radio,
        )
        rf_card.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=(18, 12))

        streaming_card, self._streaming_button = self._build_source_card(
            parent=self._chooser,
            title="STREAMING RADIO",
            eyebrow="INTERNET AUDIO",
            description="Browse local and regional streams with artwork, favorites and playback.",
            features="LOCAL  •  REGIONAL  •  FAVORITES",
            action_text="BROWSE STATIONS  ›",
            accent=ui.accent_primary,
            icon_kind="stream",
            command=self.open_streaming_radio,
        )
        streaming_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(6, 12),
            pady=(18, 12),
        )
        self._status = tk.Label(
            self._chooser,
            text="Choose a radio source",
            bg=ui.background,
            fg=ui.text_muted,
            font=("Sans", FONT_BODY),
        )
        self._status.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        self._streaming_card_appearance = OfflineCardAppearance(streaming_card)
        self._mode_changed(self._online_allowed())

    def _build_source_card(
        self,
        *,
        parent: tk.Misc,
        title: str,
        eyebrow: str,
        description: str,
        features: str,
        action_text: str,
        accent: str,
        icon_kind: str,
        command: Callable[[], None],
    ) -> tuple[tk.Frame, tk.Button]:
        ui = self._theme.ui
        card = tk.Frame(
            parent,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(2, weight=1)

        accent_bar = tk.Frame(card, bg=accent, height=6)
        accent_bar.grid(row=0, column=0, sticky="ew")
        accent_bar.grid_propagate(False)

        heading = tk.Frame(card, bg=ui.surface)
        heading.grid(row=1, column=0, sticky="ew", padx=14, pady=(18, 10))
        heading.grid_columnconfigure(1, weight=1)
        icon = tk.Canvas(
            heading,
            width=64,
            height=64,
            bg=ui.surface,
            highlightthickness=0,
            bd=0,
        )
        icon.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        draw_source_icon(icon, icon_kind=icon_kind, accent=accent, theme=self._theme)
        tk.Label(
            heading,
            text=eyebrow,
            bg=ui.surface,
            fg=accent,
            font=("Sans", FONT_CONTROL + 2, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="sw", pady=(8, 2))
        tk.Label(
            heading,
            text=title,
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 21, "bold"),
            anchor="w",
        ).grid(row=1, column=1, sticky="nw")

        body = tk.Frame(card, bg=ui.surface)
        body.grid(row=2, column=0, sticky="nsew", padx=26, pady=(8, 14))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        tk.Label(
            body,
            text=description,
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", FONT_BODY + 3),
            justify=tk.LEFT,
            anchor="nw",
            wraplength=390,
        ).grid(row=0, column=0, sticky="new")
        tk.Label(
            body,
            text=features,
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", FONT_CONTROL + 2, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(14, 8))
        button = tk.Button(
            body,
            text=action_text,
            command=command,
            bg=ui.control_background,
            fg=accent,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=ui.border,
            font=("Sans", FONT_CONTROL + 2, "bold"),
            padx=16,
            pady=10,
            cursor="hand2",
        )
        button.grid(row=2, column=0, sticky="ew", pady=(8, 0))

        for widget in self._walk_widgets(card):
            if widget is button:
                continue
            widget.bind("<Button-1>", partial(self._source_clicked, command))
            try:
                if isinstance(widget, tk.Widget):
                    widget.configure({"cursor": "hand2"})
            except tk.TclError:
                pass
        return card, button

    @staticmethod
    def _source_clicked(command: Callable[[], None], event: tk.Event) -> None:
        command()

    @staticmethod
    def _walk_widgets(root: tk.Misc) -> tuple[tk.Misc, ...]:
        widgets: list[tk.Misc] = [root]
        for child in root.winfo_children():
            widgets.extend(RadioEntryPanel._walk_widgets(child))
        return tuple(widgets)

    def _show_streaming_radio(self) -> None:
        if not self._online_allowed():
            return
        if self._radio_panel is not None:
            self._radio_panel.destroy()
            self._radio_panel = None
        self._chooser.grid_remove()
        if self._streaming_page is None or not self._streaming_page.winfo_exists():
            self._streaming_page = self._streaming_panel_factory(
                self, self._theme, self._show_chooser,
            )
        self._streaming_page.activate()
        self._streaming_page.grid(row=0, column=0, sticky="nsew")

    def _show_chooser(self) -> None:
        if self._streaming_page is not None and self._streaming_page.winfo_exists():
            self._streaming_page.deactivate()
            self._streaming_page.grid_remove()
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._set_location("RADIO")

    def _set_location(self, leaf: str) -> None:
        handler = self._on_location_changed
        if handler is not None:
            handler(leaf)

    def _launch_rf_radio(self) -> None:
        if self._streaming_page is not None:
            self._streaming_page.deactivate()
            self._streaming_page.grid_remove()
        self._chooser.grid_remove()
        if self._radio_panel is not None:
            self._radio_panel.destroy()
        self._radio_panel = self._rf_panel_factory(self, self._theme)
        self._radio_panel.grid(row=0, column=0, sticky="nsew")
        self._radio_panel.launch()

    def detach_sdrpp(self, parent_window_id: int) -> None:
        if self._radio_panel is not None:
            self._radio_panel.deactivate()
