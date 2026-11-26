"""Inline Spotify view for the Trending radio screen."""

import tkinter as tk
from collections.abc import Callable
from time import monotonic

from frontends.tk.media.spotify_playback_panel import SpotifyPlaybackPanel
from ui.media.spotify_browse_if import SpotifyLocalPlayerState, SpotifyPlaybackMode


def build_trending_spotify_pane(
    parent: tk.Misc,
    on_back: Callable[[], None],
    artist: str,
    title: str,
    *,
    theme: dict,
    activate: Callable[[SpotifyPlaybackPanel], Callable[[], None]],
    report_status: Callable[[str], None],
    dispatch_ui: Callable[[Callable[[], None]], None],
    android: bool,
    network_allowed: Callable[[], bool],
    request_song: Callable[[str, str, Callable[[str], None]], None],
    player_state: Callable[[], SpotifyLocalPlayerState],
    request_player: Callable[[], None],
    configured: bool,
    on_setup: Callable[[], None],
) -> tk.Widget:
    colors = theme["colors"]
    host = tk.Frame(parent, bg=colors["background"])
    host.grid_rowconfigure(1, weight=1)
    host.grid_columnconfigure(0, weight=1)
    back = tk.Button(
        host,
        text="‹ BACK",
        command=on_back,
        bg=colors["button_background"],
        fg=colors["button_foreground"],
        activebackground=colors["button_active_background"],
        activeforeground=colors["button_active_foreground"],
        relief=tk.FLAT,
        font=("Sans", 11, "bold"),
        padx=12,
        pady=8,
    )
    back.grid(row=0, column=0, sticky="w")
    if not configured:
        setup = tk.Frame(host, bg=colors["card_background"], padx=16, pady=16)
        setup.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        tk.Label(
            setup,
            text="Set up Spotify",
            bg=colors["card_background"],
            fg=colors["title"],
            font=("Sans", 16, "bold"),
        ).pack(pady=(12, 8))
        tk.Button(
            setup,
            text="OPEN SPOTIFY SETUP",
            command=on_setup,
            bg=colors["button_active_background"],
            fg=colors["button_active_foreground"],
            relief=tk.FLAT,
            font=("Sans", 11, "bold"),
            padx=12,
            pady=8,
        ).pack()
        return host
    panel = SpotifyPlaybackPanel(host, theme=theme, show_video=False)
    panel.grid(row=1, column=0, sticky="nsew")
    retire_session = activate(panel)
    status = tk.Label(
        host,
        text=f"Looking up {artist} - {title}…",
        bg=theme["colors"]["background"],
        fg=colors["subtitle"],
        anchor="w",
        wraplength=340,
    )
    status.grid(row=2, column=0, sticky="ew", padx=8, pady=3)
    status.bind("<Configure>", lambda event: status.configure(wraplength=max(1, event.width - 8)))

    def report(message: str) -> None:
        def update() -> None:
            if host.winfo_exists():
                status.configure(text=message)
                report_status(message)

        dispatch_ui(update)

    # On Termux, Spotify plays in the Android app. Never launch the SDK browser.
    if android:
        # The existing Spotify presentation already supplies metadata,
        # artwork, progress, and controls from Spotify Web API. Do not
        # duplicate or overwrite its status with MediaSession polling.
        # Android Bridge remains available as a separate transport adapter.
        # Resolve the selected MusicForge song and request it on the active
        # Spotify Connect device (normally the Android Spotify app).
        # Keep Web API calls on its existing worker, never on Tk's thread.
        if network_allowed():
            request_song(artist, title, report)
            report(f"Requesting {artist} - {title} on active Spotify device")
    else:
        # Register the SDK playback device before queuing a track. The local
        # player queues its transfer first, so subsequent play uses that device.
        state = player_state()
        if not state.available:
            report("Local Spotify player unavailable: " + state.message)
        else:
            deadline = monotonic() + 25.0
            request_player()

            def await_device() -> None:
                if not host.winfo_exists() or not network_allowed():
                    return
                current = player_state()
                if current.mode is SpotifyPlaybackMode.PLAYER and not current.busy:
                    report("ORC Spotify device ready. Loading selected track…")
                    request_song(artist, title, report)
                elif current.mode is SpotifyPlaybackMode.REMOTE and not current.busy:
                    report(current.message)
                elif monotonic() >= deadline:
                    report("Timed out waiting for ORC Spotify player registration")
                else:
                    host.after(200, await_device)

            host.after(200, await_device)

    def retire(event: tk.Event) -> None:
        if event.widget is host:
            retire_session()

    host.bind("<Destroy>", retire, add="+")
    return host
