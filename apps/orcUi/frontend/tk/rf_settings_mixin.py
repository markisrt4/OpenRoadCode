# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""RF display and receiver configuration presentation."""

import tkinter as tk

from ui.radio.radio_visualization_config import (
    load_rf_visualization_settings,
    save_rf_visualization_settings,
)

from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


class RfSettingsMixin:
    """Build and operate the RF settings page."""

    def _build_rf_settings(self, body: tk.Frame) -> tk.Frame:
        ui = self._theme_bundle.ui
        rf = tk.Frame(body, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        rf.grid(row=1, column=0, sticky="ew", pady=4)
        rf.grid_columnconfigure(1, weight=1)
        tk.Label(
            rf,
            text="RF DISPLAY • ADVANCED",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=10)
        saved = load_rf_visualization_settings()
        self._rf_renderer = tk.StringVar(value=str(saved.get("renderer", "auto")))
        self._rf_palette = tk.StringVar(value=str(saved.get("palette", "classic")))
        self._rf_fps = tk.IntVar(value=int(saved.get("max_fps", 10)))
        self._rf_rows = tk.IntVar(value=int(saved.get("waterfall_rows", 180)))
        for row, (label, variable, options) in enumerate(
            (
                ("Renderer", self._rf_renderer, ("auto", "opengl", "tk")),
                ("Waterfall palette", self._rf_palette, ("classic", "grayscale")),
                ("Maximum display FPS", self._rf_fps, (5, 10, 15, 20, 30)),
                ("Waterfall history rows", self._rf_rows, (60, 120, 180, 256, 360)),
            ),
            start=1,
        ):
            tk.Label(rf, text=label, bg=ui.surface, fg=ui.text, font=("Sans", FONT_BODY)).grid(
                row=row, column=0, sticky="w", padx=14, pady=6
            )
            selector = tk.OptionMenu(rf, variable, *options)
            selector.configure(
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground=ui.text,
                relief=tk.FLAT,
                bd=0,
                highlightthickness=0,
                indicatoron=False,
                font=("Sans", FONT_CONTROL, "bold"),
                anchor="w",
                padx=12,
                pady=7,
            )
            selector["menu"].configure(
                bg=ui.surface_alt,
                fg=ui.text,
                activebackground=ui.accent_primary,
                activeforeground="#ffffff",
                font=("Sans", FONT_CONTROL),
                bd=0,
            )
            selector.grid(row=row, column=1, sticky="ew", padx=14, pady=6)
        tk.Label(
            rf,
            text="RECEIVER • RTL-SDR",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 11, "bold"),
        ).grid(row=7, column=0, columnspan=2, sticky="w", padx=14, pady=(16, 8))
        self._rf_gain = tk.StringVar(value="29.7")
        self._rf_ppm = tk.StringVar(value="0")
        self._rf_agc = tk.BooleanVar(value=False)
        for row, label, variable in (
            (8, "Tuner gain (dB; blank = auto)", self._rf_gain),
            (9, "Frequency correction (PPM)", self._rf_ppm),
        ):
            tk.Label(rf, text=label, bg=ui.surface, fg=ui.text, font=("Sans", FONT_BODY)).grid(
                row=row, column=0, sticky="w", padx=14, pady=5
            )
            tk.Entry(
                rf,
                textvariable=variable,
                bg=ui.control_background,
                fg=ui.control_text,
                insertbackground=ui.text,
                relief=tk.FLAT,
                font=("Sans", FONT_CONTROL),
            ).grid(row=row, column=1, sticky="ew", padx=14, pady=5)
        tk.Checkbutton(
            rf,
            text="RTL digital AGC",
            variable=self._rf_agc,
            bg=ui.surface,
            fg=ui.text,
            selectcolor=ui.control_background,
            activebackground=ui.surface,
            activeforeground=ui.text,
        ).grid(row=10, column=0, columnspan=2, sticky="w", padx=14)
        tk.Label(
            rf,
            text="WBFM sample rate: 2.4 Msps (fixed). Stop SDR before applying hardware changes.",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", FONT_SMALL),
        ).grid(row=11, column=0, columnspan=2, sticky="w", padx=14, pady=6)
        self._rf_hardware_status = tk.Label(
            rf, text="", bg=ui.surface, fg=ui.text_muted, font=("Sans", FONT_SMALL)
        )
        self._rf_hardware_status.grid(row=12, column=0, columnspan=2, sticky="w", padx=14)
        tk.Button(
            rf,
            text="APPLY RECEIVER SETTINGS",
            command=self._apply_rf_hardware,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            relief=tk.FLAT,
            font=("Sans", FONT_CONTROL, "bold"),
        ).grid(row=13, column=0, columnspan=2, sticky="ew", padx=14, pady=8)
        self._rf_saved_label = tk.Label(
            rf,
            text="Changes apply when the radio view is reopened.",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", FONT_SMALL),
        )
        self._rf_saved_label.grid(row=5, column=0, columnspan=2, sticky="w", padx=14, pady=6)
        tk.Button(
            rf,
            text="SAVE RF SETTINGS",
            command=self._save_rf_settings,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            relief=tk.FLAT,
            font=("Sans", FONT_CONTROL, "bold"),
        ).grid(row=6, column=0, columnspan=2, sticky="ew", padx=14, pady=12)
        return rf

    def _rf_status(self, message: str) -> None:
        """Schedule status updates on Tk's presentation thread."""
        try:
            self.after(0, lambda: self._rf_hardware_status.configure(text=message))
        except RuntimeError:
            pass

    def _load_rf_hardware(self) -> None:
        """Request receiver settings through the injected RF configuration port."""
        if self._rf_hardware_config is None:
            self._rf_hardware_status.configure(text="Receiver configuration unavailable.")
            return
        self._rf_hardware_status.configure(text="Loading receiver configuration...")

        def loaded(config) -> None:
            def apply() -> None:
                self._rf_gain.set("" if config.get("gain_db") is None else str(config["gain_db"]))
                self._rf_ppm.set(str(config.get("ppm_correction", 0)))
                self._rf_agc.set(bool(config.get("rtl_agc_enabled", False)))
                self._rf_hardware_status.configure(text="Receiver settings loaded from SDRForge.")

            try:
                self.after(0, apply)
            except RuntimeError:
                pass

        self._rf_hardware_config.load(
            loaded, lambda message: self._rf_status(f"Unable to read SDRForge settings: {message}")
        )

    def _apply_rf_hardware(self) -> None:
        if self._rf_hardware_config is None:
            self._rf_hardware_status.configure(text="Receiver configuration unavailable.")
            return
        try:
            gain = self._rf_gain.get().strip()
            payload = {
                "sample_rate_hz": 2400000,
                "gain_db": None if not gain else float(gain),
                "ppm_correction": int(self._rf_ppm.get()),
                "rtl_agc_enabled": self._rf_agc.get(),
            }
        except ValueError:
            self._rf_hardware_status.configure(text="Invalid gain or PPM value")
            return
        self._rf_hardware_status.configure(text="Applying receiver settings...")
        self._rf_hardware_config.apply(
            payload,
            lambda: self._rf_status("Receiver settings applied. Start SDR to use them."),
            lambda message: self._rf_status(f"Receiver settings not applied: {message}"),
        )

    def _save_rf_settings(self) -> None:
        save_rf_visualization_settings(
            {
                "renderer": self._rf_renderer.get(),
                "palette": self._rf_palette.get(),
                "max_fps": self._rf_fps.get(),
                "waterfall_rows": self._rf_rows.get(),
            }
        )
        self._rf_saved_label.configure(text="Saved. Reopen the radio view to apply.")
