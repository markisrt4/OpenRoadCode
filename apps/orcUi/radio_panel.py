# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling the SDR++ X11 client."""

from __future__ import annotations

import tkinter as tk

from apps.orcUi.radio_control import OrcUiRadioControl, OrcUiRadioState
from apps.orcUi.sdrpp_control import OrcUiSdrppControl
from frontends.x11 import X11WindowEmbedder

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
RED = "#f15a16"

MAIN_GROUPS = (
    ("FM", "♫ FM"),
    ("WEATHER", "☁ WEATHER"),
    ("AIR", "✈ AIR"),
    ("HAM", "⌁ HAM"),
    ("SCANNER", "⌁ SCANNER"),
)
SCANNER_GROUPS = (
    ("PUBLIC SAFETY", "★ PUBLIC SAFETY"),
    ("FIRE/EMS", "✚ FIRE / EMS"),
    ("LAW", "◆ LAW"),
    ("RAIL", "▰ RAIL"),
    ("MARINE", "≈ MARINE"),
    ("AVIATION", "✈ AVIATION"),
    ("BUSINESS", "▣ BUSINESS"),
    ("UTILITIES", "⚡ UTILITIES"),
)
RADIO_GROUPS = tuple(name for name, _ in MAIN_GROUPS)


class RadioPanel(tk.Frame):
    """Automotive controls wrapped around an embedded SDR++ viewport."""

    def __init__(self, parent: tk.Misc, *, embedder: X11WindowEmbedder | None = None, radio_control: OrcUiRadioControl | None = None, sdrpp_control: OrcUiSdrppControl | None = None) -> None:
        super().__init__(parent, bg=BG)
        self._embedder = embedder or X11WindowEmbedder()
        self._radio = radio_control or OrcUiRadioControl()
        self._sdrpp = sdrpp_control or OrcUiSdrppControl()
        self._active_group = "FM"
        self._group_buttons: dict[str, tk.Button] = {}
        self._drawer_open = False
        self._drawer: tk.Frame | None = None
        self._display_buttons: dict[str, tk.Button] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._groups = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self._groups.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self._show_main_groups()

        self._body = tk.Frame(self, bg=BG)
        self._body.grid(row=1, column=0, sticky="nsew")
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)
        self._host = tk.Frame(self._body, bg="#000000", highlightthickness=1, highlightbackground=BORDER)
        self._host.grid(row=0, column=0, sticky="nsew")
        self._host.bind("<Configure>", self._on_host_resize)

        controls = tk.Frame(self, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        controls.grid(row=2, column=0, sticky="ew", pady=(6, 0))
        controls.grid_columnconfigure(2, weight=1)
        tk.Button(controls, text="‹ PRESET", command=self._previous_preset, bg=PANEL, fg=TEXT, relief=tk.FLAT, bd=0, padx=12, pady=7).grid(row=0, column=0, rowspan=2, sticky="ns")
        tk.Button(controls, text="− TUNE", command=self._tune_down, bg=PANEL, fg=MUTED, relief=tk.FLAT, bd=0, padx=10, pady=7).grid(row=0, column=1, rowspan=2, sticky="ns")
        center = tk.Frame(controls, bg=PANEL); center.grid(row=0, column=2, rowspan=2, sticky="ew")
        self._station_label = tk.Label(center, text="NO PRESET", bg=PANEL, fg=TEXT, font=("Sans", 11, "bold")); self._station_label.pack()
        self._frequency_label = tk.Label(center, text="--.- MHz", bg=PANEL, fg=MUTED, font=("Monospace", 9)); self._frequency_label.pack()
        tk.Button(controls, text="TUNE +", command=self._tune_up, bg=PANEL, fg=MUTED, relief=tk.FLAT, bd=0, padx=10, pady=7).grid(row=0, column=3, rowspan=2, sticky="ns")
        tk.Button(controls, text="PRESET ›", command=self._next_preset, bg=PANEL, fg=TEXT, relief=tk.FLAT, bd=0, padx=12, pady=7).grid(row=0, column=4, rowspan=2, sticky="ns")
        self._apply_radio_state(self._radio.state)

    def _clear_group_bar(self) -> None:
        for widget in self._groups.winfo_children():
            widget.destroy()
        self._group_buttons.clear()

    def _nav_button(self, key: str, label: str, command, *, expand: bool = True) -> tk.Button:
        button = tk.Button(self._groups, text=label, command=command, bg=PANEL, fg=TEXT, activebackground="#17232d", activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=9, pady=7)
        button.pack(side=tk.LEFT, fill=tk.X, expand=expand)
        self._group_buttons[key] = button
        return button

    def _show_main_groups(self) -> None:
        self._clear_group_bar()
        for name, label in MAIN_GROUPS:
            command = self._show_scanner_groups if name == "SCANNER" else lambda group=name: self.select_group(group)
            self._nav_button(name, label, command)
        self._controls_button = tk.Button(self._groups, text="☰ CONTROLS", command=self._toggle_drawer, bg=PANEL, fg=TEXT, activebackground="#17232d", activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 9, "bold"), padx=12, pady=7)
        self._controls_button.pack(side=tk.RIGHT)
        self._paint_groups()

    def _show_scanner_groups(self) -> None:
        self._active_group = "SCANNER"
        self._clear_group_bar()
        self._nav_button("BACK", "‹ BACK", self._show_main_groups, expand=False)
        for name, label in SCANNER_GROUPS:
            self._nav_button(name, label, lambda group=name: self._select_scanner_group(group))
        self._paint_groups()

    def _select_scanner_group(self, name: str) -> None:
        self._active_group = name
        self._paint_groups()

    @property
    def host_window_id(self) -> int:
        self.update_idletasks(); return int(self._host.winfo_id())

    @property
    def active_group(self) -> str: return self._active_group

    def select_group(self, name: str) -> None:
        if name not in RADIO_GROUPS: raise ValueError(f"Unknown radio group: {name}")
        self._active_group = name; self._paint_groups()

    def set_station(self, label: str, frequency_hz: int, mode_name: str | None = None) -> None:
        self._station_label.configure(text=label)
        suffix = f"   {mode_name}" if mode_name else ""
        self._frequency_label.configure(text=f"{frequency_hz / 1_000_000:.3f} MHz{suffix}", fg=MUTED)

    def attach_sdrpp(self, process_id: int = 0) -> int:
        self.update_idletasks()
        return self._embedder.embed(process_id, self.host_window_id, self._host.winfo_width(), self._host.winfo_height(), window_name="SDR++")

    def detach_sdrpp(self, parent_window_id: int) -> None: self._embedder.detach(parent_window_id)
    def clear_embedding(self) -> None: self._embedder.clear()

    def _toggle_drawer(self) -> None:
        if self._drawer_open:
            if self._drawer is not None: self._drawer.place_forget()
            self._drawer_open = False
            self._controls_button.configure(fg=TEXT, bg=PANEL)
            return
        if self._drawer is None: self._build_drawer()
        self._drawer.place(relx=1.0, rely=0.0, relheight=1.0, width=250, anchor="ne")
        self._drawer.lift(); self._drawer_open = True
        self._controls_button.configure(fg=GREEN, bg="#101820")
        self._refresh_display_controls()

    def _build_drawer(self) -> None:
        self._drawer = tk.Frame(self._body, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        header = tk.Frame(self._drawer, bg="#101820"); header.pack(fill=tk.X)
        tk.Label(header, text="RADIO CONTROLS", bg="#101820", fg=TEXT, font=("Sans", 11, "bold"), padx=12, pady=10).pack(side=tk.LEFT)
        tk.Button(header, text="✕", command=self._toggle_drawer, bg="#101820", fg=MUTED, activeforeground=TEXT, relief=tk.FLAT, bd=0, padx=12, pady=10).pack(side=tk.RIGHT)
        for key, label, action in (("waterfall", "WATERFALL", self._toggle_waterfall), ("bandplan", "BANDPLAN", self._toggle_bandplan), ("fft_hold", "PEAK HOLD", self._toggle_fft_hold)):
            button = tk.Button(self._drawer, text=label, command=action, anchor="w", bg=PANEL, fg=MUTED, activebackground="#17232d", activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=16, pady=13)
            button.pack(fill=tk.X); self._display_buttons[key] = button
        tk.Frame(self._drawer, bg=BORDER, height=1).pack(fill=tk.X, padx=12, pady=4)
        tk.Button(self._drawer, text="AUTO RANGE", command=self._auto_range, anchor="w", bg=PANEL, fg=TEXT, activebackground="#17232d", activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=16, pady=13).pack(fill=tk.X)

    def _paint_toggle(self, key: str, label: str, enabled: bool) -> None:
        self._display_buttons[key].configure(text=f"{label}     {'ON' if enabled else 'OFF'}", fg=GREEN if enabled else MUTED, bg="#101820" if enabled else PANEL)

    def _remote_toggle(self, key: str, label: str, action) -> None:
        try: self._paint_toggle(key, label, action())
        except (OSError, RuntimeError, ValueError) as error:
            self._display_buttons[key].configure(text=f"{label}     !", fg=RED)
            print(f"WARNING: SDR++ remote control: {type(error).__name__}: {error}")

    def _toggle_waterfall(self) -> None: self._remote_toggle("waterfall", "WATERFALL", self._sdrpp.toggle_waterfall)
    def _toggle_bandplan(self) -> None: self._remote_toggle("bandplan", "BANDPLAN", self._sdrpp.toggle_bandplan)
    def _toggle_fft_hold(self) -> None: self._remote_toggle("fft_hold", "PEAK HOLD", self._sdrpp.toggle_fft_hold)

    def _auto_range(self) -> None:
        try: self._sdrpp.auto_range()
        except (OSError, RuntimeError, ValueError) as error: print(f"WARNING: SDR++ auto range: {type(error).__name__}: {error}")

    def _refresh_display_controls(self) -> None:
        for key, label, getter in (("waterfall", "WATERFALL", self._sdrpp.waterfall_visible), ("bandplan", "BANDPLAN", self._sdrpp.bandplan_visible), ("fft_hold", "PEAK HOLD", self._sdrpp.fft_hold_enabled)):
            try: self._paint_toggle(key, label, getter())
            except (OSError, RuntimeError, ValueError): self._display_buttons[key].configure(text=label, fg=MUTED, bg=PANEL)

    def _previous_preset(self) -> None: self._run_radio_action(self._radio.previous_preset)
    def _next_preset(self) -> None: self._run_radio_action(self._radio.next_preset)
    def _tune_down(self) -> None: self._run_radio_action(self._radio.tune_down)
    def _tune_up(self) -> None: self._run_radio_action(self._radio.tune_up)

    def _run_radio_action(self, action) -> None:
        try: self._apply_radio_state(action())
        except (OSError, RuntimeError, ValueError) as error:
            self._frequency_label.configure(text=f"RIGCTL: {error}", fg=RED)
            print(f"WARNING: SDR++ rigctl: {type(error).__name__}: {error}")

    def _apply_radio_state(self, state: OrcUiRadioState) -> None: self.set_station(state.label, state.frequency_hz, state.mode_name)
    def _on_host_resize(self, event: tk.Event) -> None: self._embedder.resize(event.width, event.height)
    def _paint_groups(self) -> None:
        for name, button in self._group_buttons.items():
            active = name == self._active_group
            button.configure(fg=GREEN if active else TEXT, bg="#101820" if active else PANEL)
