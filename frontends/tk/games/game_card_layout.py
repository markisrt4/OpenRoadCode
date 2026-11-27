# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fit the Games card footer to the available Tk grid width."""

import tkinter as tk


def bind_game_card_layout(
    card: tk.Frame,
    name: tk.Label,
    description: tk.Label,
    status: tk.Label,
    action: tk.Button,
) -> None:
    status_padding = (4, 6)
    action_padding = (4, 8)
    status.grid(row=2, column=1, sticky="ew", padx=status_padding, pady=(1, 5))
    action.grid(row=2, column=2, sticky="ew", padx=action_padding, pady=9)

    def resize(event: tk.Event) -> None:
        # The card border takes one pixel on either side of the grid.
        content_width = max(1, event.width - 70 - 2)
        status_width = status.winfo_reqwidth() + sum(status_padding)
        action_width = action.winfo_reqwidth() + sum(action_padding)
        if status_width + action_width <= content_width:
            card.grid_columnconfigure(1, minsize=status_width)
            card.grid_columnconfigure(2, minsize=action_width)
            status.grid_configure(columnspan=1)
            action.grid_configure(row=2, column=2, columnspan=1)
        else:
            card.grid_columnconfigure(1, minsize=0)
            card.grid_columnconfigure(2, minsize=0)
            status.grid_configure(columnspan=2)
            action.grid_configure(row=3, column=1, columnspan=2)
        wrap = max(1, content_width - sum(status_padding) - 4)
        name.configure(wraplength=wrap)
        description.configure(wraplength=wrap)

    card.bind("<Configure>", resize)
