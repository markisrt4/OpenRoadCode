# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Streaming-radio presentation with persistent favorite identifiers."""

from __future__ import annotations

import tkinter as tk

from collections.abc import Callable
from ui.radio.streaming_radio_session_if import StreamingRadioSessionIf
from ui.radio.streaming_radio_types import StreamingRadioStation
from frontends.tk.radio.streaming_radio_panel import (
    BG,
    BLUE,
    BORDER,
    CARD,
    CARD_SELECTED,
    DANGER,
    GREEN,
    MUTED,
    PANEL,
    TEXT,
    StreamingRadioPanel,
)
from ui.theme import ThemeBundle


class PersistentStreamingRadioPanel(StreamingRadioPanel):
    """Apply the ORC theme to contract-driven streaming presentation."""

    def __init__(
        self, parent: tk.Misc, *, session: StreamingRadioSessionIf, theme: ThemeBundle,
        on_back: Callable[[], None],
        on_station_selected: Callable[[StreamingRadioStation], None] | None = None,
    ) -> None:
        self._theme_bundle = theme
        super().__init__(parent, session=session, on_back=on_back,
                         on_station_selected=on_station_selected)
        self._apply_theme()

    def set_theme_bundle(self, theme: ThemeBundle) -> None:
        """Apply the current ORC semantic theme to the legacy streaming widgets."""
        previous = self._theme_bundle
        self._theme_bundle = theme
        self._render_stations()
        self._apply_theme(previous)

    def _render_stations(self) -> None:
        super()._render_stations()
        self._apply_theme()

    def _paint_filters(self) -> None:
        super()._paint_filters()
        self._apply_theme()

    def _paint_playback_status(self) -> None:
        super()._paint_playback_status()
        self._apply_theme()

    def _build_filter_drawer(self) -> None:
        super()._build_filter_drawer()
        self._apply_theme()

    def _show_status(self, text: str, *, danger: bool = False) -> None:
        super()._show_status(text, danger=danger)
        self._apply_theme()

    def _apply_theme(self, previous: ThemeBundle | None = None) -> None:
        if not hasattr(self, "_theme_bundle"):
            return
        ui = self._theme_bundle.ui
        colors = {
            BG: ui.background,
            PANEL: ui.surface,
            CARD: ui.surface_alt,
            CARD_SELECTED: ui.control_active,
            BORDER: ui.border,
            TEXT: ui.text,
            MUTED: ui.text_muted,
            GREEN: ui.accent_success,
            BLUE: ui.accent_primary,
            DANGER: ui.accent_danger,
            "#142619": ui.surface_alt,
            "#081018": ui.control_background,
            "#071006": ui.control_text,
            "#9bdc45": ui.control_active,
            "#ffffff": ui.text,
        }
        if previous is not None:
            old = previous.ui
            colors.update(
                {
                    old.background: ui.background,
                    old.surface: ui.surface,
                    old.surface_alt: ui.surface_alt,
                    old.border: ui.border,
                    old.text: ui.text,
                    old.text_muted: ui.text_muted,
                    old.accent_primary: ui.accent_primary,
                    old.accent_success: ui.accent_success,
                    old.accent_danger: ui.accent_danger,
                    old.control_background: ui.control_background,
                    old.control_active: ui.control_active,
                    old.control_text: ui.control_text,
                }
            )
        self._recolor_widget_tree(self, colors)

    @classmethod
    def _recolor_widget_tree(cls, widget: tk.Misc, colors: dict[str, str]) -> None:
        for option in (
            "background",
            "foreground",
            "activebackground",
            "activeforeground",
            "disabledforeground",
            "highlightbackground",
        ):
            try:
                current = str(widget.cget(option)).lower()
            except tk.TclError:
                continue
            replacement = colors.get(current)
            if replacement is not None and replacement.lower() != current:
                try:
                    widget.configure(**{option: replacement})
                except tk.TclError:
                    pass
        for child in widget.winfo_children():
            cls._recolor_widget_tree(child, colors)
