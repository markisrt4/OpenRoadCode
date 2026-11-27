# SPDX-License-Identifier: MIT
"""Render connected receivers and edit their RF assignments."""

import tkinter as tk
from tkinter import ttk

from ui import UiWidget
from ui.radio.receiver_settings_if import ReceiverSettingsIf, ReceiverSettingsState
from ui.theme import ThemeBundle

from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


class ReceiverSettingsPanel(tk.Frame, UiWidget):
    """Display assigned receivers and forward semantic settings requests."""

    def __init__(self, parent: tk.Misc, requests: ReceiverSettingsIf, theme: ThemeBundle) -> None:
        color = theme.ui
        super().__init__(parent, bg=color.surface)
        self._requests = requests
        self._choices: list[tk.StringVar] = []
        self._selectors: list[ttk.Combobox] = []
        self._pending = False
        self.columnconfigure(1, weight=1)
        self._inventory = tk.Label(
            self, bg=color.surface, fg=color.text, justify="left", font=("Sans", FONT_SMALL)
        )
        self._inventory.grid(row=0, column=0, columnspan=2, sticky="w", pady=(8, 4))
        for row, label in enumerate(("Radio / Airband", "NOAA Weather Radio", "ADS-B"), start=1):
            tk.Label(
                self, text=label, bg=color.surface, fg=color.text, font=("Sans", FONT_BODY)
            ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
            variable = tk.StringVar(value="")
            selector = ttk.Combobox(
                self, textvariable=variable, state="readonly", font=("Sans", FONT_BODY)
            )
            selector.grid(row=row, column=1, sticky="ew", pady=4)
            self._choices.append(variable)
            self._selectors.append(selector)
        self._status = tk.Label(
            self, bg=color.surface, fg=color.text_muted, justify="left", font=("Sans", FONT_SMALL)
        )
        self._status.grid(row=4, column=0, columnspan=2, sticky="w")
        self._buttons = []
        for column, text, command in (
            (0, "REFRESH RECEIVERS", self.refresh),
            (1, "SAVE ASSIGNMENTS", self._save),
        ):
            button = tk.Button(
                self,
                text=text,
                command=command,
                bg=color.control_background,
                fg=color.control_text,
                activebackground=color.control_active,
                relief=tk.FLAT,
                font=("Sans", FONT_CONTROL, "bold"),
            )
            button.grid(row=5, column=column, sticky="ew", padx=(0, 8), pady=6)
            self._buttons.append(button)
        self._buttons[1].configure(state="disabled")

    def _busy(self, text: str) -> bool:
        if self._pending:
            return False
        self._pending = True
        self._status.configure(text=text)
        for button in self._buttons:
            button.configure(state="disabled")
        return True

    def refresh(self) -> None:
        if self._busy("Discovering receivers…"):
            self._requests.refresh(self._render, self._error)

    def _save(self) -> None:
        if self._busy("Saving assignments…"):
            radio, weather, adsb = (value.get() or None for value in self._choices)
            self._requests.save(radio, weather, adsb, self._saved, self._error)

    def _finish(self, message: str, *, allow_save: bool) -> bool:
        if not self.winfo_exists():
            return False
        self._pending = False
        self._status.configure(text=message)
        self._buttons[0].configure(state="normal")
        self._buttons[1].configure(state="normal" if allow_save else "disabled")
        return True

    def _error(self, message: str) -> None:
        self._finish(message, allow_save=False)

    def _saved(self, state: ReceiverSettingsState) -> None:
        self._render(state, "Receiver assignments saved")

    def _render(self, state: ReceiverSettingsState, message: str = "") -> None:
        if not self._finish(message, allow_save=True):
            return
        options = tuple(
            device.identity for device in state.receivers if device.available and device.identity
        )
        lines = []
        for receiver in state.receivers:
            description = (
                f"{receiver.owner} · {receiver.phase or 'Reserved'}"
                if receiver.owner
                else "Available"
                if receiver.available
                else "Missing serial or duplicate identity"
            )
            lines.append(
                f"{receiver.serial or '(no serial)'}  ·  USB {receiver.usb_path}  ·  {description}"
            )
        assigned = (state.radio, state.weather, state.adsb)
        connected = {device.identity for device in state.receivers}
        for name, identity in zip(("Radio", "Weather", "ADS-B"), assigned, strict=True):
            if identity and identity not in connected:
                lines.append(f"{name}: {identity} disconnected")
        self._inventory.configure(text="\n".join(lines) or "No supported USB receivers connected")
        for selector, variable, identity in zip(
            self._selectors, self._choices, assigned, strict=True
        ):
            retained = (identity,) if identity is not None and identity not in options else ()
            selector.configure(values=("", *options, *retained))
            variable.set(identity or "")
