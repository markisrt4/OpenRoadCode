# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Driver-facing diagnostic results; widgets consume presentation contracts only."""
import tkinter as tk
from tkinter import ttk

from ui.automotive.diagnostics_scan_if import DiagnosticsScanHandlerIf, DiagnosticsScanState
from ui.theme import ThemeBundle
from ui.ui_widget import UiWidget


class VehicleDiagnosticsPanel(tk.Frame, UiWidget):
    """Keep scan controls visible above scrollable explanations and fault cards."""

    def __init__(self, parent, *, theme: ThemeBundle,
                 handler: DiagnosticsScanHandlerIf | None = None):
        self._ui = theme.ui
        self._handler = handler
        self._state = DiagnosticsScanState()
        self._expanded = False
        self._wrap_labels = []
        super().__init__(parent, bg=self._ui.surface_alt, highlightthickness=1,
                         highlightbackground=self._ui.border)
        ui = self._ui
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        header = tk.Frame(self, bg=ui.surface_alt)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        self._scan = tk.Button(header, text="Scan Now", command=self._request_scan,
                               bg=ui.control_background, fg=ui.control_text,
                               activebackground=ui.control_active, activeforeground=ui.control_text,
                               relief=tk.FLAT, padx=14, pady=8)
        self._scan.pack(side=tk.RIGHT, padx=(8, 0))
        self._summary = tk.Label(header, bg=ui.surface_alt, fg=ui.text, font=("Sans", 18, "bold"),
                                 anchor="w", justify=tk.LEFT, wraplength=320)
        self._summary.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._timestamp = tk.Label(self, bg=ui.surface_alt, fg=ui.text_muted,
                                   anchor="w", font=("Sans", 10))
        self._timestamp.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        self._progress = ttk.Progressbar(self, mode="indeterminate")
        self._progress.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        self._progress.grid_remove()

        body = tk.Frame(self, bg=ui.surface_alt)
        body.grid(row=3, column=0, sticky="nsew")
        rail = tk.Frame(body, bg=ui.surface_alt)
        rail.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas = tk.Canvas(body, bg=ui.surface_alt, highlightthickness=0,
                                 width=320, height=220, takefocus=True)
        for title, direction in (("▲", -1), ("▼", 1)):
            tk.Button(rail, text=title, command=lambda d=direction: self._canvas.yview_scroll(d * 3, "units"),
                      bg=ui.control_background, fg=ui.control_text, relief=tk.FLAT,
                      padx=8, pady=8).pack(side=tk.TOP if direction < 0 else tk.BOTTOM)
        scrollbar = tk.Scrollbar(rail, command=self._canvas.yview)
        scrollbar.pack(fill=tk.Y, expand=True)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._content = tk.Frame(self._canvas, bg=ui.surface_alt)
        self._window = self._canvas.create_window(0, 0, anchor="nw", window=self._content)
        self._content.bind("<Configure>", lambda _event: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", self._resize)
        self._canvas.bind("<Up>", lambda _event: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Down>", lambda _event: self._canvas.yview_scroll(1, "units"))
        self.update_diagnostics(self._state)

    def _request_scan(self):
        if self._handler is not None:
            self._handler.request_scan()

    def update_diagnostics(self, state: DiagnosticsScanState):
        if state == self._state and self._wrap_labels:
            return
        self._state = state
        ui = self._ui
        color = {"faulted": ui.accent_warning, "healthy": ui.accent_success,
                 "scanning": ui.accent_primary, "not_ready": ui.accent_warning}.get(state.status, ui.text_muted)
        self._summary.configure(text=state.summary, fg=color)
        self._scan.configure(text="Scanning…" if state.scanning else "Scan Now",
                             state=tk.DISABLED if state.scanning or self._handler is None else tk.NORMAL)
        if state.scanning:
            self._progress.grid()
            self._progress.start(60)
        else:
            self._progress.stop()
            self._progress.grid_remove()
        timestamp = ("Scan finished " + state.completed_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
                     if state.completed_at is not None else
                     "Reading diagnostic information…" if state.scanning else "No completed scan")
        self._timestamp.configure(text=timestamp)
        self._render()
        self._canvas.yview_moveto(0)

    def _label(self, parent, text, *, bold=False, color=None, background=None):
        label = tk.Label(parent, text=text, bg=background or self._ui.surface_alt,
                         fg=color or self._ui.text, anchor="w", justify=tk.LEFT,
                         font=("Sans", 12, "bold") if bold else ("Sans", 12), wraplength=280)
        label.pack(fill=tk.X, anchor="w", padx=12, pady=4)
        self._wrap_labels.append(label)
        return label

    def _render(self):
        for child in self._content.winfo_children():
            child.destroy()
        self._wrap_labels = []
        state, ui = self._state, self._ui
        self._label(self._content, state.coverage_message,
                    color=ui.text_muted if state.coverage_complete else ui.accent_warning)
        if not state.scanning:
            light = "On" if state.mil_on is True else "Off" if state.mil_on is False else "Unavailable"
            self._label(self._content, "Check Engine light: " + light, bold=True)
            readiness = ("Checks complete" if state.emissions_ready is True else
                         "Checks unfinished — this alone does not mean a fault" if state.emissions_ready is False else
                         "Unavailable — the vehicle did not provide enough information")
            self._label(self._content, "Emissions readiness: " + readiness)
        self._label(self._content, "What does this mean?", bold=True)
        self._label(self._content, state.next_action)
        for fault in state.faults:
            card = tk.Frame(self._content, bg=ui.surface, highlightthickness=1,
                            highlightbackground=ui.border)
            card.pack(fill=tk.X, padx=12, pady=6)
            self._label(card, fault.title, bold=True, background=ui.surface)
            self._label(card, fault.reporting_status, color=ui.accent_warning, background=ui.surface)
            self._label(card, fault.explanation, background=ui.surface)
            self._label(card, "Suggested next step", bold=True, background=ui.surface)
            self._label(card, fault.recommendation, background=ui.surface)
        self._details_button = tk.Button(
            self._content, text="Hide technical details" if self._expanded else "Show technical details",
            command=self._toggle_details, bg=ui.control_background, fg=ui.control_text,
            relief=tk.FLAT, pady=8)
        self._details_button.pack(fill=tk.X, padx=12, pady=10)
        if self._expanded:
            self._label(self._content, state.details, color=ui.text_muted)
        self._resize_labels()
        self._bind_scroll(self._content)
        self._bind_scroll(self._canvas)

    def _toggle_details(self):
        self._expanded = not self._expanded
        self._render()
        self._details_button.focus_set()

    def _bind_scroll(self, widget):
        widget.bind("<MouseWheel>", lambda event: self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units"))
        widget.bind("<Button-4>", lambda _event: self._canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda _event: self._canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children():
            # The canvas owns content too; recursion runs once from _content.
            if widget is not self._canvas:
                self._bind_scroll(child)

    def _resize(self, event):
        self._canvas.itemconfigure(self._window, width=event.width)
        self._summary.configure(wraplength=max(120, event.width - 140))
        self._resize_labels()

    def _resize_labels(self):
        width = max(160, self._canvas.winfo_width() - 52)
        for label in self._wrap_labels:
            label.configure(wraplength=width)

    def destroy(self):
        self._progress.stop()
        super().destroy()
