"""Render a cached artist biography and credited Wikimedia portrait."""

import tkinter as tk
from io import BytesIO

from PIL import Image, ImageTk

from ui.media.artist_profile import ArtistProfile
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class TrendingArtistDetails(tk.Frame, UiWidget):
    """Display artist context using only the injected profile snapshot."""

    def __init__(self, parent: tk.Misc, theme: ThemeBundle) -> None:
        ui = theme.ui
        super().__init__(parent, bg=ui.surface)
        self._title = tk.Label(self, bg=ui.surface, fg=ui.text, font=("Sans", 20, "bold"))
        self._subtitle = tk.Label(self, bg=ui.surface, fg=ui.text_muted, font=("Sans", 13))
        self._title.pack(fill=tk.X, pady=(18, 4))
        self._subtitle.pack(fill=tk.X, pady=(0, 6))
        self._portrait = tk.Label(self, bg=ui.surface)
        self._bio = tk.Label(self, bg=ui.surface, fg=ui.text, justify=tk.LEFT, font=("Sans", 11))
        self._credit = tk.Label(
            self, bg=ui.surface, fg=ui.text_muted, justify=tk.LEFT, font=("Sans", 9)
        )
        self._bio.pack(fill=tk.X, pady=(8, 4))
        self._credit.pack(fill=tk.X)
        self._photo: ImageTk.PhotoImage | None = None
        self.bind("<Configure>", self._resize)

    def _resize(self, event: tk.Event) -> None:
        for label in (self._title, self._subtitle, self._bio, self._credit):
            label.configure(wraplength=max(1, event.width - 8))

    def set_selection(self, title: str, subtitle: str) -> None:
        if self._title.cget("text") != title:
            self.set_profile(None)
        self._title.configure(text=title)
        self._subtitle.configure(text=subtitle)

    def set_profile(self, profile: ArtistProfile | None) -> None:
        """Clear previous content and render a new artist snapshot."""
        self._portrait.pack_forget()
        self._portrait.configure(image="")
        self._photo = None
        self._bio.configure(text=profile.biography if profile else "")
        self._credit.configure(
            text=f"About {profile.name} · Wikipedia (CC BY-SA)" if profile else ""
        )
        if profile is None or not profile.portrait:
            return
        try:
            with Image.open(BytesIO(profile.portrait)) as image:
                image.thumbnail((280, 152))
                self._photo = ImageTk.PhotoImage(image, master=self)
        except (OSError, ValueError):
            return
        self._portrait.configure(image=self._photo)
        self._portrait.pack(before=self._bio)
        self._credit.configure(
            text=f"About {profile.name} · Wikipedia (CC BY-SA)\nPhoto: {profile.portrait_credit}"
        )
