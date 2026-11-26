# SPDX-License-Identifier: MIT
"""Render playback and Bluetooth receiver controls on the Settings page."""

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from ui.system.audio_settings_if import (
    AudioAction,
    AudioDevice,
    AudioSettingsIf,
    AudioSettingsState,
)
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget

from .shell_metrics import FONT_BODY, FONT_CONTROL


class AudioSettingsPanel(tk.Frame, UiWidget):
    """Present an audio snapshot and submit semantic requests."""

    def __init__(self, parent: tk.Misc, requests: AudioSettingsIf, theme: ThemeBundle) -> None:
        color = theme.ui
        super().__init__(parent, bg=color.surface, padx=14, pady=10)
        self._requests = requests
        self._state = AudioSettingsState()
        self._busy = False
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        def heading(row: int, label: str) -> None:
            tk.Label(
                self, text=label, bg=color.surface, fg=color.text, font=("Sans", FONT_BODY, "bold")
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 2))

        def button(row: int, column: int, label: str, command: Callable[[], None]) -> tk.Button:
            widget = tk.Button(
                self,
                text=label,
                command=command,
                bg=color.control_background,
                fg=color.control_text,
                activebackground=color.control_active,
                relief=tk.FLAT,
                font=("Sans", FONT_CONTROL, "bold"),
                pady=6,
            )
            widget.grid(row=row, column=column, sticky="ew", padx=2, pady=3)
            return widget

        heading(0, "PLAYBACK OUTPUT")
        self._outputs = ttk.Combobox(self, state="readonly")
        self._outputs.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._apply = button(2, 0, "SET DEFAULT OUTPUT", self._select_output)
        self._refresh = button(2, 1, "REFRESH", self.refresh)

        heading(3, "BLUETOOTH AUDIO RECEIVERS")
        self._receivers = ttk.Combobox(self, state="readonly")
        self._receivers.grid(row=4, column=0, columnspan=2, sticky="ew")
        self._connect = button(5, 0, "CONNECT", self._change_connection)
        self._scan = button(5, 1, "SCAN", lambda: self._submit(AudioAction.SCAN))
        self._status = tk.Label(
            self, bg=color.surface, fg=color.text_muted, justify=tk.LEFT, anchor="w"
        )
        self._status.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.bind(
            "<Configure>",
            lambda event: self._status.configure(wraplength=max(160, event.width - 28)),
        )
        self._receivers.bind("<<ComboboxSelected>>", lambda _event: self._update_buttons())
        self._update_buttons()

    def refresh(self) -> None:
        self._submit(AudioAction.REFRESH)

    @staticmethod
    def _selected(widget: ttk.Combobox, devices: tuple[AudioDevice, ...]) -> AudioDevice | None:
        index = widget.current()
        return devices[index] if 0 <= index < len(devices) else None

    def _select_output(self) -> None:
        output = self._selected(self._outputs, self._state.outputs)
        if output is not None:
            self._submit(AudioAction.SELECT_OUTPUT, output.identifier)

    def _change_connection(self) -> None:
        receiver = self._selected(self._receivers, self._state.receivers)
        if receiver is not None:
            action = AudioAction.DISCONNECT if receiver.selected else AudioAction.CONNECT
            self._submit(action, receiver.identifier)

    def _update_buttons(self) -> None:
        receiver = self._selected(self._receivers, self._state.receivers)
        self._apply.configure(
            state=tk.NORMAL if self._state.outputs and not self._busy else tk.DISABLED
        )
        self._refresh.configure(state=tk.DISABLED if self._busy else tk.NORMAL)
        self._scan.configure(state=tk.DISABLED if self._busy else tk.NORMAL)
        self._connect.configure(
            text=(
                "DISCONNECT"
                if receiver and receiver.selected
                else "PAIR & CONNECT"
                if receiver and not receiver.paired
                else "CONNECT"
            ),
            state=tk.NORMAL if receiver and not self._busy else tk.DISABLED,
        )

    def _submit(self, action: AudioAction, identifier: str = "") -> None:
        if self._busy:
            return
        self._busy = True
        self._update_buttons()
        self._status.configure(
            text="Scanning for receivers…" if action is AudioAction.SCAN else "Checking audio…"
        )
        self._requests.request(action, identifier, self._render, self._error)

    def _render(self, state: AudioSettingsState) -> None:
        if not self.winfo_exists():
            return
        previous = self._selected(self._receivers, self._state.receivers)
        self._state = state
        self._outputs.configure(
            values=tuple(
                f"{item.name} (default)" if item.selected else item.name for item in state.outputs
            )
        )
        if state.outputs:
            self._outputs.current(
                next((i for i, item in enumerate(state.outputs) if item.selected), 0)
            )
        else:
            self._outputs.set("No playback outputs")
        self._receivers.configure(
            values=tuple(
                f"{item.name} ({'connected' if item.selected else 'paired' if item.paired else 'unpaired'}) · {item.identifier}"
                for item in state.receivers
            )
        )
        if state.receivers:
            self._receivers.current(
                next(
                    (
                        i
                        for i, item in enumerate(state.receivers)
                        if previous and item.identifier == previous.identifier
                    ),
                    0,
                )
            )
        else:
            self._receivers.set("No Bluetooth audio receivers")
        self._error("\n".join(state.warnings))

    def _error(self, message: str) -> None:
        if self.winfo_exists():
            self._busy = False
            self._update_buttons()
            self._status.configure(text=message)
