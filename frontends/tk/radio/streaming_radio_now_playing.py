# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Home-screen radio summary with streaming playback awareness."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from ui.radio.streaming_radio_state_source_if import StreamingRadioStateSourceIf
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class StreamingRadioNowPlaying(tk.Frame, UiWidget):
    """Present neutral radio state and current streaming playback on Home."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        state_source: StreamingRadioStateSourceIf,
        theme: ThemeBundle,
        on_open_rf: Callable[[], None],
        on_open_streaming: Callable[[], None],
        on_open_adsb: Callable[[], None],
        online_allowed: Callable[[], bool] = lambda: True,
    ) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.surface)
        self._online_allowed = online_allowed
        self._state_source = state_source
        self._ui = ui
        self._after_id: str | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(1, weight=0)

        self._status = tk.Label(
            self,
            text="RADIO",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 9, "bold"),
            anchor="w",
        )
        # HOME card already provides the RADIO heading; show status only when on air.
        self._status.grid(row=0, column=0, sticky="ew", padx=10, pady=(3, 0))
        self._status.grid_remove()

        source_shortcuts = tk.Frame(self, bg=ui.surface)
        source_shortcuts.grid(row=1, column=0, columnspan=2, sticky="ew", padx=9, pady=(5, 3))
        for column in range(3):
            source_shortcuts.grid_columnconfigure(column, weight=1)

        # Large icon above the label, both inside the same touch target.
        def source_button(column: int, icon: str, label: str, color: str,
                          command: Callable[[], None]) -> tk.Canvas:
            tile = tk.Canvas(source_shortcuts, width=56, height=66,
                             bg=ui.control_background, highlightthickness=0,
                             bd=0, cursor="hand2")
            tile.grid(row=0, column=column, sticky="nsew",
                      padx=(0, 3) if column == 0 else ((3, 0) if column == 2 else 3))
            def paint(_event: tk.Event | None = None) -> None:
                tile.delete("all")
                width = max(1, tile.winfo_width())
                tile.create_text(width / 2, 24, text=icon, fill=color,
                                 font=("Sans", 22, "bold"))
                tile.create_text(width / 2, 53, text=label, fill=color,
                                 font=("Sans", 9, "bold"))
            tile.bind("<Configure>", paint)
            tile.bind("<Button-1>", lambda _event: command()
                      if label != "STREAM" or self._online_allowed() else None)
            return tile

        self._adsb_button = source_button(0, "✈", "ADS-B", ui.accent_warning, on_open_adsb)
        self._rf_button = source_button(1, "◉", "RF", ui.accent_success, on_open_rf)
        self._stream_button = source_button(2, "♫", "STREAM", ui.accent_primary, on_open_streaming)

        self._station = tk.Label(
            self,
            text="No radio active",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 15, "bold"),
            anchor="w",
            justify=tk.LEFT,
            wraplength=200,
        )
        self._station.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 1))

        self._detail = tk.Label(
            self,
            text="Choose RF or streaming",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 9),
            anchor="w",
        )
        self._detail.grid(row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 9))

        self._refresh()

    def destroy(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None
        super().destroy()

    def _refresh(self) -> None:
        if not self.winfo_exists():
            return
        online = self._online_allowed()
        self._stream_button.configure(cursor="hand2" if online else "arrow")
        state = self._state_source.snapshot()
        current = state.station
        playing = current is not None and state.is_playing
        if playing and current is not None:
            self._status.configure(text="● ON AIR • STREAM", fg=self._ui.accent_success)
            self._status.grid()
            self._station.configure(text=current.name)
            details: list[str] = []
            if current.state:
                details.append(current.state)
            if current.codec:
                details.append(current.codec)
            if current.bitrate_kbps is not None:
                details.append(f"{current.bitrate_kbps} kbps")
            self._detail.configure(text=" • ".join(details) or "Streaming radio")

        else:
            self._status.grid_remove()
            self._station.configure(text="Radio idle")
            self._detail.configure(text="Choose a source to start listening" if online else "Offline • RF available")

        self._after_id = self.after(750, self._refresh)
