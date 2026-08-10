from __future__ import annotations

import tkinter as tk
from typing import Any

from ui.system import StatusUiIf, StatusValue


class StatusBarPanel(tk.Frame, StatusUiIf):
    """Persistent bottom shell panel for application status messages."""

    def __init__(
        self,
        parent: tk.Widget,
        *,
        theme: dict[str, Any],
        compact_ui: bool,
        initial_status: str = "Ready",
    ) -> None:
        self._theme = theme
        self._colors = theme["colors"]
        self._layout = theme["layout"]
        self._style = theme["profiles"][
            "compact" if compact_ui else "normal"
        ]

        super().__init__(
            parent,
            bg=self._colors["background"],
        )

        self._status_var = tk.StringVar(value=initial_status)

        self._label = tk.Label(
            self,
            textvariable=self._status_var,
            anchor=self._layout["anchor"],
            bg=self._colors["background"],
            fg=self._colors["foreground"],
            font=self._style["font"],
            padx=self._style["padx"],
            pady=self._style["pady"],
        )
        self._label.pack(
            fill=self._layout["fill"],
            side=self._layout["side"],
        )

    def set_status(self, status: StatusValue) -> None:
        """Present a structured or concise application status."""
        if status is None:
            text = ""
        elif isinstance(status, str):
            text = status
        else:
            parts = [status.summary]
            if status.detail:
                parts.append(status.detail)
            text = " — ".join(parts)
            if status.source:
                text = f"{status.source}: {text}"
        self._status_var.set(text)

    def get_status(self) -> str:
        return self._status_var.get()
