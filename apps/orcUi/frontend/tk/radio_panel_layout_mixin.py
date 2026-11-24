# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""orcUi radio panel hosting and controlling external radio presentations."""

from __future__ import annotations

import tkinter as tk
from .sdrforge_receiver_view import SdrForgeReceiverView
from .automotive_radio_button import AutomotiveRadioButton
from ui.radio.sdrforge_spectrum_if import SpectrumPresentation
from ui.radio.radio_visualization_config import RadioVisualizationConfig
from ui.radio.rf_radio_if import RadioAction, RadioHost, RadioRequest, RfRadioSession, RfRadioState, receiver_mode_mismatch
from ui.radio.radio_profile_state import RadioProfileState
from ui.theme import ThemeBundle
from .shell_metrics import FONT_SMALL
from .radio_display_controls import RadioDisplayControlsMixin
from .radio_group_menu import MAIN_GROUPS, RadioGroupMenuMixin


class RadioPanelLayoutMixin:
    """Build the receiver layout and controls."""

    def _build_radio_layout(self, *, ui, native_sdrforge, theme, visualization) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._groups = tk.Frame(
            self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
        )
        self._groups.grid(row=0, column=0, sticky="ew", pady=(0, 3))
        self._subcategory_strip = tk.Frame(self, bg=ui.surface)
        self._subcategory_signature = None

        self._build_group_bar()
        self._body = tk.Frame(self, bg=ui.background)
        self._body.grid(row=1, column=0, sticky="nsew")
        self._body.grid_columnconfigure(0, weight=1)
        self._body.grid_rowconfigure(0, weight=1)
        self._host = tk.Frame(
            self._body, bg=ui.background, highlightthickness=1, highlightbackground=ui.border
        )
        self._host.grid(row=0, column=0, sticky="nsew")
        self._host.bind("<Configure>", self._on_host_resize)
        self._sdrforge_view: SdrForgeReceiverView | None = None
        self._sdrforge_after_id: str | None = None
        if native_sdrforge:
            self._sdrforge_view = SdrForgeReceiverView(self._host, theme=theme,
                                                      visualization=visualization)
            self._sdrforge_view.place(relx=0, rely=0, relwidth=1, relheight=1)
            self._sdrforge_view.set_spectrum_tune_handler(self._tune_spectrum_frequency)
            self._sdrforge_view.set_recenter_handler(self._recenter_spectrum)
            self._sdrforge_view.set_tune_step_handler(self._gesture_tune)
            self._poll_sdrforge_spectrum()

        self._telemetry_overlay = tk.Frame(
            self._host, bg=ui.surface_alt, highlightthickness=1, highlightbackground=ui.border
        )
        self._telemetry_overlay.place(relx=1.0, x=-8, y=8, anchor="ne")
        self._signal_label = tk.Label(
            self._telemetry_overlay,
            text="SIGNAL --",
            bg=ui.surface_alt,
            fg=ui.text,
            font=("Monospace", 8, "bold"),
            padx=8,
            pady=3,
        )
        self._signal_label.pack(side=tk.LEFT)
        self._snr_label = tk.Label(
            self._telemetry_overlay,
            text="SNR --",
            bg=ui.surface_alt,
            fg=ui.accent_success,
            font=("Monospace", 8, "bold"),
            padx=8,
            pady=3,
        )
        self._snr_label.pack(side=tk.LEFT)

        self._controls = tk.Frame(
            self, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border
        )
        self._controls.grid(row=2, column=0, sticky="ew", pady=(2, 0))
        for column in range(5):
            self._controls.grid_columnconfigure(column, weight=1 if native_sdrforge else (1 if column == 2 else 0))
        tk.Button(
            self._controls,
            text="◀  STATION",
            command=self._previous_preset,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=12 if native_sdrforge else 7,
            highlightthickness=0,
        ).grid(row=0, column=0, rowspan=3, sticky="nsew" if native_sdrforge else "ns")
        tk.Button(
            self._controls,
            text="◀  TUNE",
            command=self._tune_down,
            bg=ui.surface,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=12 if native_sdrforge else 7,
            highlightthickness=0,
        ).grid(row=0, column=1, rowspan=3, sticky="nsew" if native_sdrforge else "ns")
        center = tk.Frame(self._controls, bg=ui.surface)
        center.grid(row=0, column=2, rowspan=3, sticky="ew")
        self._station_label = tk.Label(
            center, text="FM RADIO", bg=ui.surface, fg=ui.text, font=("Sans", 15, "bold")
        )
        self._station_label.pack()
        self._frequency_label = tk.Label(
            center, text="--.--- MHz", bg=ui.surface, fg=ui.text_muted, font=("Monospace", 9)
        )
        self._frequency_label.pack()
        self._metadata_label = tk.Label(
            center, text="", bg=ui.surface, fg=ui.accent_success, font=("Sans", FONT_SMALL)
        )
        self._metadata_label.pack()
        if native_sdrforge:
            center.grid_remove()  # Frequency and station already appear in the receiver header.
            self._controls.grid_columnconfigure(2, weight=0, minsize=0)
        tk.Button(
            self._controls,
            text="TUNE  ▶",
            command=self._tune_up,
            bg=ui.surface,
            fg=ui.text_muted,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=7,
            highlightthickness=0,
        ).grid(row=0, column=3, rowspan=3, sticky="nsew" if native_sdrforge else "ns")
        tk.Button(
            self._controls,
            text="STATION  ▶",
            command=self._next_preset,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=7,
            highlightthickness=0,
        ).grid(row=0, column=4, rowspan=3, sticky="nsew" if native_sdrforge else "ns")

        self._receiver_controls = None
        if native_sdrforge:
            self._controls.grid_remove()
            # Keep a generous FFT viewport at 1280x720 while allowing smaller
            # windowed launches to retain usable tuning controls.
            self._body.grid_columnconfigure(1, weight=0, minsize=320)
            self.bind("<Configure>", self._resize_receiver_sidebar, add="+")
            self._receiver_controls = tk.Frame(
                self._body, bg=ui.surface, width=320,
                highlightthickness=1, highlightbackground=ui.border)
            self._receiver_controls.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
            self._receiver_controls.grid_propagate(False)
            self._receiver_controls.grid_rowconfigure(1, minsize=132)
            for col in (0, 1):
                self._receiver_controls.grid_columnconfigure(col, weight=1, uniform="tuning")
            self._subcategory_strip = tk.Frame(self._receiver_controls, bg=ui.surface)
            self._subcategory_strip.grid(row=1, column=0, columnspan=2,
                                         sticky="new", padx=5, pady=(0, 4))
            for tile_column in range(2):
                self._subcategory_strip.grid_columnconfigure(tile_column, weight=1,
                                                               uniform="bands")
            self._station_info = tk.Frame(self._receiver_controls, bg=ui.surface)
            self._station_info.grid(row=1, column=0, columnspan=2,
                                    sticky="nsew", padx=8, pady=4)
            self._info_title = tk.Label(self._station_info, text="RDS  •  WAITING",
                                        bg=ui.surface, fg=ui.accent_primary,
                                        font=("Sans", 10, "bold"), anchor="w")
            self._info_title.pack(fill=tk.X)
            self._info_name = tk.Label(self._station_info, text="No station ID",
                                       bg=ui.surface, fg=ui.text,
                                       font=("Sans", 13, "bold"), anchor="w")
            self._info_name.pack(fill=tk.X)
            self._info_text = tk.Label(self._station_info, text="Waiting for RDS data",
                                       bg=ui.surface, fg=ui.text_muted,
                                       font=("Sans", 9), anchor="nw", justify="left",
                                       wraplength=288)
            self._info_text.pack(fill=tk.X)
            # Discovery occupies the existing right-hand information slot.
            # Canvas provides touch and wheel navigation with no visible scrollbar.
            # Full-height overlay over the right sidebar, not a cramped grid row.
            # The spectrum keeps its width and the discovery list gets the
            # entire available radio workspace height.
            self._scan_card = tk.Frame(
                self._body, bg=ui.surface, highlightthickness=1,
                highlightbackground=ui.border)
            scan_header = tk.Frame(self._scan_card, bg=ui.surface)
            scan_header.pack(fill=tk.X)
            tk.Label(scan_header, text="STATION DISCOVERY", bg=ui.surface,
                     fg=ui.accent_primary, font=("Sans", 10, "bold")).pack(side=tk.LEFT)
            tk.Button(scan_header, text="CLOSE", command=self._close_scan_results,
                      bg=ui.control_background, fg=ui.text, relief=tk.FLAT).pack(side=tk.RIGHT)
            self._scan_canvas = tk.Canvas(self._scan_card, bg=ui.surface,
                                           highlightthickness=0)
            self._scan_canvas.pack(fill=tk.BOTH, expand=True)
            self._scan_status = tk.Label(
                self._scan_card, text="Ready to scan", bg=ui.surface,
                fg=ui.text_muted, font=("Sans", 9), anchor="w")
            self._scan_status.pack(fill=tk.X, padx=8, pady=(2, 3))
            self._scan_canvas.bind("<Configure>", lambda _event: self._render_scan_results())
            self._scan_canvas.bind("<ButtonPress-1>", self._scan_touch_start)
            self._scan_canvas.bind("<B1-Motion>", self._scan_touch_move)
            self._scan_canvas.bind("<ButtonRelease-1>", self._scan_touch_end)
            self._scan_canvas.bind("<MouseWheel>", self._scan_wheel)
            self._scan_canvas.bind("<Button-4>", lambda event: self._scan_scroll(-1))
            self._scan_canvas.bind("<Button-5>", lambda event: self._scan_scroll(1))
            self._scan_save = tk.Button(
                self._scan_card, text="SAVE SELECTED",
                command=self._save_scanned_presets, bg=ui.control_background,
                fg=ui.text, relief=tk.FLAT)
            self._scan_save.pack(fill=tk.X, pady=(3, 0))
            self._scan_card.place_forget()
            self._bands_heading = tk.Label(self._receiver_controls, text="BANDS", bg=ui.surface,
                     fg=ui.accent_primary, font=("Sans", 11, "bold"),
                     anchor="w", padx=10, pady=2)
            self._bands_heading.grid(row=0, column=0, columnspan=2, sticky="ew")
            tk.Label(self._receiver_controls, text="TUNING", bg=ui.surface,
                     fg=ui.accent_primary, font=("Sans", 10, "bold"),
                     anchor="w", padx=10, pady=2).grid(
                         row=2, column=0, columnspan=2, sticky="ew")
            for label, callback, row, col in (
                ("◀  STEP −", self._tune_down, 3, 0),
                ("+ STEP  ▶", self._tune_up, 3, 1),
                ("◀  PRESET", self._previous_preset, 4, 0),
                ("PRESET  ▶", self._next_preset, 4, 1),
            ):
                button = AutomotiveRadioButton(self._receiver_controls, text=label,
                                      command=callback, height=44,
                                      background=ui.control_background,
                                      accent=ui.accent_primary,
                                      foreground=ui.text, border=ui.border)
                button.grid(row=row, column=col, sticky="nsew", padx=2, pady=2)
                button.set_enabled(False)
                self._live_rf_buttons.append(button)
            self._scan_button = AutomotiveRadioButton(
                self._receiver_controls, text="SCAN BAND", command=self._toggle_scan,
                height=44, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border)
            self._scan_button.grid(row=5, column=0, sticky="nsew", padx=2, pady=2)
            self._scan_button.set_enabled(False)
            self._live_rf_buttons.append(self._scan_button)
            self._play_button = AutomotiveRadioButton(
                self._receiver_controls, text="🔇 MUTE", command=self._toggle_play,
                height=44, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border)
            self._play_button.grid(row=5, column=1, sticky="nsew", padx=2, pady=2)
            self._play_button.set_enabled(False)
            self._live_rf_buttons.append(self._play_button)
            self._receiver_power_button = AutomotiveRadioButton(
                self._receiver_controls, text="▶ START SDR",
                command=self._toggle_receiver_power,
                height=44, background=ui.control_background,
                accent=ui.accent_primary, foreground=ui.text, border=ui.border)
            self._receiver_power_button.grid(
                row=6, column=0, columnspan=2, sticky="nsew", padx=2, pady=2)
            self._receiver_mode_label = tk.Label(
                self._receiver_controls, text="MODE  --", bg=ui.surface,
                fg=ui.text_muted, font=("Sans", 9), anchor="w", padx=8, pady=2)
            # Mode is presented exclusively on the spectrum toolbar.
            # This row is informational; no new controls or scrollbars are needed.
            self._receiver_signal_label = tk.Label(
                self._receiver_controls, text="SIGNAL  --", bg=ui.surface,
                fg=ui.text_muted, font=("Sans", 10), anchor="w", padx=12, pady=8)
            self._receiver_signal_label.grid(row=7, column=0, columnspan=2, sticky="ew")

        self._favorites = tk.Frame(self, bg=ui.surface)
        if native_sdrforge:
            self._favorites.grid(row=3, column=0, sticky="ew", pady=(2, 0))
        self._launch_status = tk.Label(self._host, text="Connecting to radio…", bg=ui.background,
                                       fg=ui.text, font=("Sans", 12, "bold"), justify="center")
        self._session.bind(self)
        self._schedule_telemetry_refresh()

