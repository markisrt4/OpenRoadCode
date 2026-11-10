# SPDX-License-Identifier: MIT
"""Declared Tk presentation fields shared by the receiver menu and drawer."""
from abc import ABC, abstractmethod
import tkinter as tk

from ui.radio.rf_radio_if import RfRadioSession, RfRadioState
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class RadioPresentationFrame(tk.Frame, UiWidget, ABC):
    """A rendering-only base; composition still supplies the receiver session."""

    _theme: ThemeBundle
    _session: RfRadioSession
    _state: RfRadioState
    _active_group: str
    _groups: tk.Frame
    _body: tk.Frame
    _group_buttons: dict[str, tk.Button]
    _controls_button: tk.Button
    _drawer: tk.Frame | None
    _drawer_open: bool
    _display_buttons: dict[str, tk.Button]

    @abstractmethod
    def _toggle_drawer(self) -> None:
        """Toggle the frontend-only display control drawer."""

    @abstractmethod
    def _show_adsb(self) -> None:
        """Emit an aircraft presentation request."""
