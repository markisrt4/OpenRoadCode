# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radio scan result presentation and selection gestures."""

import tkinter as tk

from ui.radio.rf_radio_if import RadioAction, RadioRequest


class RadioScanMixin:
    """Render scan results and submit semantic scan requests."""

    def _toggle_scan(self) -> None:
        if self._sdrforge_view is not None and not self._state.receiver_running:
            return
        action = RadioAction.STOP_SCAN if self._state.scanning else RadioAction.SCAN
        if action is RadioAction.SCAN:
            self._scan_requested = True
            self._scan_signature = None
            self._scan_dismissed = False
            self._scan_selected.clear()
        self._session.request(RadioRequest(action))

    def _close_scan_results(self) -> None:
        self._scan_signature = None
        self._scan_dismissed = True
        self._scan_requested = False
        self._scan_selected.clear()
        self._scan_card.place_forget()
        self._show_radio_info()

    def _show_radio_info(self) -> None:
        group = self._active_group.split(":", 1)[0]
        if group in ("FM", "WEATHER"):
            self._subcategory_strip.grid_remove()
            self._station_info.grid()
        else:
            self._station_info.grid_remove()
            self._subcategory_strip.grid()

    def _scan_touch_start(self, event: tk.Event) -> None:
        self._scan_drag_y = event.y
        self._scan_dragged = False

    def _scan_touch_move(self, event: tk.Event) -> None:
        if self._scan_drag_y is None:
            return
        delta = self._scan_drag_y - event.y
        if abs(delta) >= 6:
            self._scan_dragged = True
            self._scan_canvas.yview_scroll(int(delta / 12) or (1 if delta > 0 else -1), "units")
            self._scan_drag_y = event.y

    def _scan_touch_end(self, event: tk.Event) -> None:
        if not self._scan_dragged:
            x = self._scan_canvas.canvasx(event.x)  # type: ignore[no-untyped-call]
            y = self._scan_canvas.canvasy(event.y)  # type: ignore[no-untyped-call]
            # A tap on empty space must not select the nearest station.
            item = self._scan_canvas.find_overlapping(x, y, x, y)
            if item:
                tags = self._scan_canvas.gettags(item[-1])
                for tag in tags:
                    if tag.startswith("frequency_"):
                        self._toggle_scan_hit(int(tag.removeprefix("frequency_")))
                        break
        self._scan_drag_y = None

    def _scan_scroll(self, units: int) -> None:
        self._scan_canvas.yview_scroll(units, "units")

    def _scan_wheel(self, event: tk.Event) -> None:
        self._scan_scroll(-1 if event.delta > 0 else 1)

    def _toggle_scan_hit(self, frequency: int) -> None:
        if self._scan_dragged:
            return
        if frequency in self._scan_selected:
            self._scan_selected.remove(frequency)
        else:
            self._scan_selected.add(frequency)
        self._render_scan_results()

    def _render_scan_results(self) -> None:
        canvas = self._scan_canvas
        previous_scroll = canvas.yview()[0]
        canvas.delete("all")
        ui = self._theme.ui
        width = max(250, canvas.winfo_width())
        if not self._state.scan_hits:
            message = "Scanning…" if self._state.scanning else "0 stations found"
            canvas.create_text(
                width // 2,
                55,
                text=message,
                fill=ui.text,
                font=("Sans", 12, "bold"),
                anchor="center",
            )
        for index, frequency in enumerate(self._state.scan_hits):
            y = index * 36
            selected = frequency in self._scan_selected
            canvas.create_rectangle(
                2,
                y + 2,
                width - 4,
                y + 33,
                fill=ui.control_background if selected else ui.surface,
                outline=ui.border,
                tags=(f"frequency_{frequency}",),
            )
            canvas.create_text(
                12,
                y + 18,
                anchor="w",
                text=("☑ " if selected else "□ ") + f"{frequency / 1_000_000:.3f} MHz",
                fill=ui.text,
                font=("Sans", 10, "bold"),
                tags=(f"frequency_{frequency}",),
            )
        canvas.configure(scrollregion=(0, 0, width, max(1, len(self._state.scan_hits) * 36)))
        canvas.yview_moveto(previous_scroll)
        self._scan_save.configure(
            text=f"SAVE SELECTED ({len(self._scan_selected)})",
            state=tk.NORMAL
            if self._scan_selected and self._state.presets_writable
            else tk.DISABLED,
        )

    def _save_scanned_presets(self) -> None:
        if not self._state.presets_writable:
            return
        key = self._state.station.profile_key
        for frequency in sorted(self._scan_selected):
            self._session.request(
                RadioRequest(
                    RadioAction.ADD_PRESET,
                    key=key,
                    label=f"{frequency / 1_000_000:.3f} MHz",
                    frequency_hz=frequency,
                )
            )
        saved_count = len(self._scan_selected)
        self._scan_selected.clear()
        self._scan_status.configure(text=f"Save requested for {saved_count} preset(s)")
        self._render_scan_results()
