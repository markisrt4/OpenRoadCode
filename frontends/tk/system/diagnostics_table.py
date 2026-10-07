# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compact ORC rows with semantic colors, independent of native ttk styling."""

import tkinter as tk
from tkinter import font


class DiagnosticsTable(tk.Frame):
    """Small selectable list retaining full row values for detail views."""

    def __init__(self, parent, *, theme, columns, visible):
        ui = theme.ui
        super().__init__(parent, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        self._ui = ui
        self._columns = columns
        self._visible = [column for column in columns if column[0] in visible]
        self._rows = {}
        self._order = []
        self._selection = ()
        self._tags = {}
        self._pending = None
        self._font = font.Font(self, family="Sans", size=11)
        self._heading_font = font.Font(self, family="Sans", size=9, weight="bold")
        self._row_height = 36
        self._header = tk.Canvas(self, bg=ui.surface_alt, height=32, highlightthickness=0)
        self._header.pack(fill=tk.X)
        body = tk.Frame(self, bg=ui.surface)
        body.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(body, bg=ui.surface, highlightthickness=0, takefocus=True)
        scroll = tk.Scrollbar(body, command=self._canvas.yview, bg=ui.control_background,
                              activebackground=ui.control_active, troughcolor=ui.surface, relief=tk.FLAT, bd=0)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.configure(yscrollcommand=scroll.set)
        self._canvas.bind("<Configure>", lambda event: self._queue_paint())
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<Up>", lambda event: self._step(-1))
        self._canvas.bind("<Down>", lambda event: self._step(1))
        self._canvas.bind("<MouseWheel>", lambda event: self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"))
        self._canvas.bind("<Button-4>", lambda event: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>", lambda event: self._canvas.yview_scroll(1, "units"))
        self.bind("<Destroy>", self._destroyed, add="+")

    def exists(self, key):
        return key in self._rows

    def item(self, key, **changes):
        self._rows[key].update(changes)
        self._queue_paint()
        return self._rows[key]

    def insert(self, parent, index, *, iid, values, tags=()):
        self._rows[iid] = {"values": values, "tags": tags}
        self._order.insert(len(self._order) if index == tk.END else int(index), iid)
        self._queue_paint()

    def move(self, key, parent, index):
        self._order.remove(key)
        self._order.insert(int(index), key)
        self._queue_paint()

    def delete(self, *keys):
        for key in keys:
            self._rows.pop(key, None)
            if key in self._order:
                self._order.remove(key)
        self._selection = tuple(key for key in self._selection if key in self._rows)
        self._queue_paint()

    def get_children(self):
        return tuple(self._order)

    def selection(self):
        return self._selection

    def selection_set(self, key):
        self._selection = (key,)
        self._queue_paint()

    def tag_configure(self, key, *, foreground):
        self._tags[key] = foreground

    def _queue_paint(self):
        if self._pending is None:
            self._pending = self.after_idle(self._paint)

    def _destroyed(self, event):
        if event.widget is self and self._pending is not None:
            self.after_cancel(self._pending)
            self._pending = None

    def _click(self, event):
        self._canvas.focus_set()
        index = int(self._canvas.canvasy(event.y) // self._row_height)
        if 0 <= index < len(self._order):
            self.selection_set(self._order[index])
            self.event_generate("<<TreeviewSelect>>")

    def _step(self, offset):
        if not self._order:
            return "break"
        index = self._order.index(self._selection[0]) if self._selection else 0
        index = max(0, min(len(self._order) - 1, index + offset))
        self.selection_set(self._order[index])
        self._canvas.yview_moveto(max(0, index - 2) / len(self._order))
        self.event_generate("<<TreeviewSelect>>")
        return "break"

    def _fit(self, value, width, text_font):
        text = str(value)
        if text_font.measure(text) <= width:
            return text
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if text_font.measure(text[:middle] + "…") <= width:
                low = middle
            else:
                high = middle - 1
        return text[:low] + "…"

    def _paint(self):
        self._pending = None
        self._header.delete("all")
        self._canvas.delete("all")
        width = max(1, self._canvas.winfo_width())
        total = sum(column[2] for column in self._visible)
        positions = []
        x = 0
        for key, heading, preferred in self._visible:
            size = width * preferred / total
            positions.append((key, x, size))
            self._header.create_text(x + 10, 16, text=self._fit(heading, size - 20, self._heading_font),
                                     font=self._heading_font, fill=self._ui.text_muted, anchor="w")
            x += size
        indices = {column[0]: index for index, column in enumerate(self._columns)}
        for index, key in enumerate(self._order):
            row = self._rows[key]
            selected = key in self._selection
            top = index * self._row_height
            self._canvas.create_rectangle(0, top, width, top + self._row_height,
                fill=self._ui.surface_alt if selected or index % 2 else self._ui.surface, outline="")
            if selected:
                self._canvas.create_rectangle(0, top, 3, top + self._row_height, fill=self._ui.accent_primary, outline="")
            color = next((self._tags[tag] for tag in row["tags"] if tag in self._tags), self._ui.text)
            for column, left, size in positions:
                value = row["values"][indices[column]]
                self._canvas.create_text(left + 10, top + self._row_height / 2,
                    text=self._fit(value, size - 20, self._font), font=self._font,
                    fill=color if column in {"state", "name", "cpu"} else self._ui.text, anchor="w")
            self._canvas.create_line(0, top + self._row_height, width, top + self._row_height, fill=self._ui.border)
        self._canvas.configure(scrollregion=(0, 0, width, len(self._order) * self._row_height))
