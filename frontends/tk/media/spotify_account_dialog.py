# SPDX-License-Identifier: MIT

"""Tk-owned account configuration input with no persistence or workers."""

import tkinter as tk
from collections.abc import Callable

from ui.media.spotify_account_if import (
    SpotifyAccountAction,
    SpotifyAccountRequests,
    SpotifyAccountSession,
    SpotifyAccountState,
)
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class SpotifyAccountDialog(UiWidget):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        session: SpotifyAccountSession,
        theme_bundle: Callable[[], ThemeBundle],
    ) -> None:
        self._parent = parent
        self._session = session
        self._theme_bundle = theme_bundle
        self._dialog: tk.Toplevel | None = None
        self._handler: SpotifyAccountRequests | None = None
        self._client_id: tk.StringVar | None = None
        self._status: tk.StringVar | None = None
        self._save: tk.Button | None = None
        self._hydrated = False
        self._saving = False

    def show(self) -> None:
        if self._dialog is not None:
            self._dialog.lift()
            return
        theme = self._theme_bundle().ui
        dialog = tk.Toplevel(self._parent)
        self._dialog = dialog
        self._hydrated = False
        self._saving = False
        dialog.title("Spotify configuration")
        dialog.configure(
            bg=theme.surface, highlightthickness=2, highlightbackground=theme.text_muted
        )
        dialog.transient(self._parent.winfo_toplevel())
        dialog.overrideredirect(True)
        width = min(840, int(dialog.winfo_screenwidth() * 0.9))
        compact = dialog.winfo_screenheight() < 600
        dialog.bind("<Escape>", lambda _event: self.close())
        dialog.grab_set()
        tk.Frame(dialog, bg="#1DB954", height=6).pack(fill=tk.X)
        dialog.protocol("WM_DELETE_WINDOW", self.close)
        tk.Label(
            dialog,
            text="SPOTIFY APPLICATION",
            bg=theme.surface,
            fg=theme.text,
            font=("Sans", 20 if compact else 28, "bold"),
        ).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(
            dialog,
            text="Enter the Client ID from your Spotify developer application. "
            "OpenRoadCode uses OAuth PKCE, so no client secret is required.",
            bg=theme.surface,
            fg=theme.text_muted,
            justify=tk.LEFT,
            wraplength=width - 48,
            font=("Sans", 14 if compact else 20),
        ).pack(anchor="w", padx=18, pady=(0, 12))
        self._client_id = tk.StringVar(master=dialog)
        entry = tk.Entry(
            dialog,
            textvariable=self._client_id,
            width=32,
            font=("Sans", 18 if compact else 24),
            bg=theme.control_background,
            fg=theme.control_text,
            insertbackground=theme.control_text,
        )
        entry.pack(fill=tk.X, padx=18)
        entry.focus_set()
        self._status = tk.StringVar(master=dialog)
        tk.Label(
            dialog,
            textvariable=self._status,
            bg=theme.surface,
            fg=theme.text_muted,
            font=("Sans", 14 if compact else 18),
            wraplength=width - 48,
        ).pack(anchor="w", padx=18, pady=(5, 0))
        buttons = tk.Frame(dialog, bg=theme.surface)
        buttons.pack(fill=tk.X, padx=18, pady=16)
        tk.Button(
            buttons,
            text="CANCEL",
            command=self.close,
            bg=theme.control_background,
            fg=theme.control_text,
            font=("Sans", 16, "bold"),
            padx=24,
            pady=12,
        ).pack(side=tk.RIGHT)
        self._save = tk.Button(
            buttons,
            text="SAVE",
            command=self._request_save,
            bg="#1DB954",
            fg="#000000",
            relief=tk.FLAT,
            padx=24,
            pady=12,
            font=("Sans", 16, "bold"),
        )
        self._save.pack(side=tk.RIGHT, padx=(0, 8))
        dialog.update_idletasks()
        height = dialog.winfo_reqheight()
        x = (dialog.winfo_screenwidth() - width) // 2
        y = max(0, (dialog.winfo_screenheight() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        self._session.activate(self)

    def _request_save(self) -> None:
        if self._handler is not None and self._client_id is not None:
            self._saving = True
            self._handler.request_configure(self._client_id.get())

    def set_spotify_account_handler(self, handler: SpotifyAccountRequests | None) -> None:
        self._handler = handler

    def set_spotify_account_state(self, state: SpotifyAccountState) -> None:
        if self._dialog is None:
            return
        if not self._hydrated and not state.loading and self._client_id is not None:
            if not self._client_id.get():
                self._client_id.set(state.client_id)
            self._hydrated = True
        if self._status is not None:
            self._status.set(state.message if state.error or self._saving else "")
        if self._save is not None:
            self._save.configure(state=tk.DISABLED if state.busy or state.loading else tk.NORMAL)
        if (
            self._saving
            and not state.busy
            and not state.error
            and state.action is SpotifyAccountAction.CONFIGURE
        ):
            self.close()

    def close(self) -> None:
        self._session.deactivate()
        dialog, self._dialog = self._dialog, None
        self._handler = None
        self._client_id = None
        self._status = None
        self._save = None
        self._saving = False
        if dialog is not None:
            dialog.destroy()
