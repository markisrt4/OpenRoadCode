from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

from ui.menu import MenuPage, MenuTile
from ui.menu.menu_icons import create_menu_icon


class MenuRenderer:
    """Render themed menu pages and reusable menu-style tiles."""

    def __init__(
        self,
        *,
        content_frame: tk.Frame,
        colors: dict[str, Any],
        layout: dict[str, Any],
        style: dict[str, Any],
        on_tile_clicked: Callable[[str], None],
    ) -> None:
        self._content_frame = content_frame
        self._colors = colors
        self._layout = layout
        self._style = style
        self._on_tile_clicked = on_tile_clicked

    def show_page(self, page: MenuPage) -> None:
        dashboard = tk.Frame(
            self._content_frame,
            bg=self._colors["app_bg"],
        )
        dashboard.pack(
            fill=self._layout["fill_both"],
            expand=True,
        )

        columns = max(1, page.columns)
        rows = max(1, (len(page.tiles) + columns - 1) // columns)

        for column in range(columns):
            dashboard.columnconfigure(
                column,
                weight=self._layout["fill_weight"],
                uniform="menu_column",
            )

        for row in range(rows):
            dashboard.rowconfigure(
                row,
                weight=self._layout["fill_weight"],
                uniform="menu_row",
            )

        for index, tile_spec in enumerate(page.tiles):
            row = index // columns
            column = index % columns

            tile = self.create_tile(
                parent=dashboard,
                tile=tile_spec,
                is_main_tile=True,
            )
            tile.grid(
                row=row,
                column=column,
                sticky=self._layout["sticky_fill"],
                padx=self._style["tile_grid_padx"],
                pady=self._style["tile_grid_pady"],
            )

    def create_tile(
        self,
        *,
        parent: tk.Widget,
        tile: MenuTile,
        is_main_tile: bool = False,
    ) -> tk.Frame:
        is_preset = "_preset_" in tile.key and not is_main_tile

        if is_main_tile:
            title_font = self._style["main_title_font"]
        elif is_preset:
            title_font = self._style["preset_title_font"]
        else:
            title_font = self._style["default_title_font"]

        anchor = (
            self._layout["anchor_center"]
            if is_preset
            else self._layout["anchor_left"]
        )
        justify = (
            self._layout["justify_center"]
            if is_preset
            else self._layout["justify_left"]
        )

        tile_frame = tk.Frame(
            parent,
            bg=self._colors["tile_bg"],
            highlightthickness=self._layout["tile_border_width"],
            highlightbackground=self._colors["tile_border"],
            highlightcolor=self._colors["tile_accent"],
            bd=self._layout["tile_border"],
            cursor=self._layout["tile_cursor"],
        )

        accent = tk.Frame(
            tile_frame,
            bg=self._colors["tile_accent"],
            height=self._style["accent_height"],
        )
        accent.pack(
            fill=self._layout["fill_horizontal"],
            side=self._layout["side_top"],
        )

        body = tk.Frame(tile_frame, bg=self._colors["tile_bg"])
        body.pack(
            fill=self._layout["fill_both"],
            expand=True,
            padx=self._style["body_padx"],
            pady=self._style["body_pady"],
        )

        icon = create_menu_icon(
            body,
            key=tile.key,
            size=self._style.get("icon_size", 48),
            background=self._colors["tile_bg"],
        )
        if icon is not None:
            icon.pack(anchor=anchor, pady=(0, self._style["subtitle_top_pad"]))

        self._create_label(
            body,
            text=tile.title,
            font=title_font,
            foreground=self._colors["tile_title"],
            anchor=anchor,
            justify=justify,
            wraplength=self._style["title_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            anchor=anchor,
        )

        self._create_label(
            body,
            text=tile.subtitle,
            font=self._style["subtitle_font"],
            foreground=self._colors["tile_subtitle"],
            anchor=anchor,
            justify=justify,
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            anchor=anchor,
            pady=(self._style["subtitle_top_pad"], 0),
        )

        self._create_label(
            body,
            text=tile.detail,
            font=self._style["detail_font"],
            foreground=self._colors["tile_detail"],
            anchor=anchor,
            justify=justify,
            wraplength=self._style["text_wrap"],
        ).pack(
            fill=self._layout["fill_horizontal"],
            anchor=anchor,
            pady=(self._style["detail_top_pad"], 0),
        )

        self._bind_click_recursive(tile_frame, tile.key)
        return tile_frame

    def _create_label(
        self,
        parent: tk.Widget,
        *,
        text: str,
        font: Any,
        foreground: str,
        anchor: str,
        justify: str,
        wraplength: int,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            font=font,
            bg=self._colors["tile_bg"],
            fg=foreground,
            anchor=anchor,
            justify=justify,
            wraplength=wraplength,
        )

    def _bind_click_recursive(
        self,
        widget: tk.Widget,
        key: str,
    ) -> None:
        widget.bind(
            "<Button-1>",
            lambda event, selected_key=key: self._on_tile_clicked(selected_key),
        )

        for child in widget.winfo_children():
            self._bind_click_recursive(child, key)
