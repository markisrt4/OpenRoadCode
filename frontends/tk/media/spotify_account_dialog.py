# SPDX-License-Identifier: MIT

"""Tk-owned account configuration input with no persistence or workers."""

from collections.abc import Callable
import tkinter as tk

from ui.media.spotify_account_if import (
    SpotifyAccountAction, SpotifyAccountRequests, SpotifyAccountSession, SpotifyAccountState,
)
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class SpotifyAccountDialog(UiWidget):
    def __init__(self, parent: tk.Misc, *, session: SpotifyAccountSession,
                 theme_bundle: Callable[[], ThemeBundle]) -> None:
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
        dialog.configure(bg=theme.background)
        dialog.transient(self._parent.winfo_toplevel())
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", self.close)
        tk.Label(dialog, text="SPOTIFY APPLICATION", bg=theme.background, fg=theme.text,
                 font=("Sans", 14, "bold")).pack(anchor="w", padx=18, pady=(16, 4))
        tk.Label(dialog, text="Enter the Client ID from your Spotify developer application. "
                 "OpenRoadCode uses OAuth PKCE, so no client secret is required.",
                 bg=theme.background, fg=theme.text_muted, justify=tk.LEFT, wraplength=460,
                 font=("Sans", 9)).pack(anchor="w", padx=18, pady=(0, 12))
        self._client_id = tk.StringVar(master=dialog)
        entry = tk.Entry(dialog, textvariable=self._client_id, width=52)
        entry.pack(fill=tk.X, padx=18)
        entry.focus_set()
        self._status = tk.StringVar(master=dialog)
        tk.Label(dialog, textvariable=self._status, bg=theme.background, fg=theme.text_muted,
                 font=("Sans", 8)).pack(anchor="w", padx=18, pady=(5, 0))
        buttons = tk.Frame(dialog, bg=theme.background)
        buttons.pack(fill=tk.X, padx=18, pady=16)
        tk.Button(buttons, text="CANCEL", command=self.close).pack(side=tk.RIGHT)
        self._save = tk.Button(buttons, text="SAVE", command=self._request_save,
                              bg="#1DB954", fg="#000000", relief=tk.FLAT, padx=14)
        self._save.pack(side=tk.RIGHT, padx=(0, 8))
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
        if self._saving and not state.busy and not state.error and state.action is SpotifyAccountAction.CONFIGURE:
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
