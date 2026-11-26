"""Touch controls and play counts for a page of airplay chart entries."""

import tkinter as tk
from collections.abc import Callable, Sequence

from PIL import Image, ImageDraw, ImageTk

from ui.theme import ThemeBundle


def _trend_icon(parent: tk.Misc, theme: ThemeBundle) -> ImageTk.PhotoImage:
    """Draw a pair of bent arrows for the period comparison action."""
    image = Image.new("RGBA", (72, 52))
    draw = ImageDraw.Draw(image)
    for color, path, head in (
        (
            theme.ui.accent_success,
            [(5, 22), (22, 10), (36, 17), (61, 3)],
            [(47, 3), (61, 3), (55, 15)],
        ),
        (
            theme.ui.accent_danger,
            [(5, 28), (22, 40), (36, 33), (61, 47)],
            [(47, 47), (61, 47), (55, 35)],
        ),
    ):
        draw.line(path, fill=color, width=4, joint="curve")
        draw.line(head, fill=color, width=4, joint="curve")
    return ImageTk.PhotoImage(image.resize((36, 26), Image.Resampling.LANCZOS), master=parent)


def render_chart_rows(
    parent: tk.Frame,
    theme: ThemeBundle,
    entries: Sequence[dict],
    *,
    offset: int,
    selected: dict | None,
    artists: bool,
    on_select: Callable[[dict], None],
    on_trend: Callable[[dict], None],
    on_stations: Callable[[dict], None],
) -> None:
    ui = theme.ui
    for child in parent.winfo_children():
        child.destroy()
    trend_icon = _trend_icon(parent, theme) if entries else None
    for index, item in enumerate(entries):
        active = item is selected
        background = ui.control_active if active else ui.surface_alt
        card = tk.Frame(
            parent,
            bg=background,
            padx=6,
            pady=2,
            highlightthickness=1,
            highlightbackground=ui.accent_primary if active else ui.border,
        )
        card.grid(row=index, column=0, sticky="nsew", pady=2)
        card.grid_columnconfigure(1, weight=1)
        rank = tk.Label(
            card,
            text=f"{item.get('rank', offset + index + 1):02}",
            bg=background,
            fg=ui.accent_primary,
            font=("Sans", 15, "bold"),
        )
        rank.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 7))
        title = tk.Label(
            card,
            text=item["artist"] if artists else item["title"],
            width=1,
            bg=background,
            fg=ui.text,
            anchor="w",
            justify=tk.LEFT,
            font=("Sans", 10, "bold"),
        )
        title.grid(row=0, column=1, sticky="ew")
        title.bind("<Configure>", lambda event, label=title: label.configure(wraplength=event.width))
        subtitle = tk.Label(
            card,
            text=f"{item.get('songs', 0)} songs" if artists else item["artist"],
            width=1,
            bg=background,
            fg=ui.text,
            anchor="w",
            font=("Sans", 10),
        )
        subtitle.grid(row=1, column=1, sticky="ew")
        count = item.get("plays")
        tk.Label(
            card,
            text=f"{count:,}\nplays" if isinstance(count, int) else "—\nplays",
            bg=background,
            fg=ui.text,
            font=("Sans", 10, "bold"),
        ).grid(row=0, column=2, rowspan=2, padx=4)
        for column, (symbol, action) in enumerate((("", on_trend), ("ⓘ", on_stations)), start=3):
            button = tk.Button(
                card,
                text=symbol,
                command=lambda callback=action, entry=item: callback(entry),
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground=ui.text,
                relief=tk.FLAT,
                width=2,
                padx=7,
                pady=3,
                font=("Sans", 15, "bold"),
            )
            if column == 3:
                button.configure(image=trend_icon, width=36)
                button.trend_icon = trend_icon
            button.grid(row=0, column=column, rowspan=2, sticky="ns", padx=(3, 0))
        for widget in (card, rank, title, subtitle):
            widget.bind("<Button-1>", lambda _event, entry=item: on_select(entry))
            widget.configure(cursor="hand2")
