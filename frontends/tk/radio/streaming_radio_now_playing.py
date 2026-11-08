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
        source_shortcuts.grid(row=1, column=0, columnspan=2, sticky="ew", padx=9, pady=(4, 2))
        for column in range(3):
            source_shortcuts.grid_columnconfigure(column, weight=1)

        self._adsb_button = tk.Button(
            source_shortcuts,
            text="✈  ADS-B",
            command=on_open_adsb,
            bg=ui.control_background,
            fg=ui.accent_warning,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 9, "bold"),
            padx=1,
            pady=10,
        )
        self._adsb_button.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self._rf_button = tk.Button(
            source_shortcuts,
            text="◉  RF",
            command=on_open_rf,
            bg=ui.control_background,
            fg=ui.accent_success,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 9, "bold"),
            padx=3,
            pady=12,
        )
        self._rf_button.grid(row=0, column=1, sticky="ew", padx=3)

        self._stream_button = tk.Button(
            source_shortcuts,
            text="♫  STREAM",
            command=on_open_streaming,
            bg=ui.control_background,
            fg=ui.accent_primary,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            font=("Sans", 9, "bold"),
            padx=3,
            pady=12,
        )
        self._stream_button.grid(row=0, column=2, sticky="ew", padx=(3, 0))

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
        self._stream_button.configure(state=tk.NORMAL if online else tk.DISABLED,
                                      disabledforeground=self._ui.text_muted)
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
            self._stream_button.configure(fg=self._ui.accent_success)
        else:
            self._status.grid_remove()
            self._station.configure(text="Radio idle")
            self._detail.configure(text="Choose a source to start listening" if online else "Offline • RF available")
            self._stream_button.configure(fg=self._ui.accent_primary)
        self._after_id = self.after(750, self._refresh)
