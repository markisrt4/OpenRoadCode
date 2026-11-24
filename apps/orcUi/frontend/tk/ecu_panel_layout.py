# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build the ECU dashboard cards and layout."""

from __future__ import annotations

import tkinter as tk

from .ecu_card_layout import fit_ecu_card
from .ecu_engine_gl import create_engine_gl
from .ecu_update_rate import EcuRateLabel
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL


class EcuPanelLayoutMixin:
    """Construct the dashboard layout used by EcuPanel."""

    def _build(self) -> None:
        ui = self._theme.ui
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # One composition surface lets the four cards frame the powertrain
        # instead of forcing the engine into a narrow middle column.
        cockpit = tk.Frame(self, bg=ui.background, width=640, height=420)
        cockpit.grid(row=0, column=0, sticky="nsew")

        engine = tk.Frame(cockpit, bg=ui.background)
        engine.place(relx=0.5, rely=0.5, relwidth=0.285, relheight=0.96, anchor="center")
        engine.grid_columnconfigure(0, weight=1)
        engine.grid_rowconfigure(0, weight=1)

        self._engine_canvas = tk.Canvas(
            engine,
            width=1,
            height=1,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
            bd=0,
        )
        self._engine_canvas.grid(row=0, column=0, sticky="nsew", padx=2, pady=(5, 2))
        self._engine_canvas.bind("<Configure>", lambda _e: self._paint_engine())
        self._engine_gl = create_engine_gl(
            engine,
            theme=self._theme,
            on_failure=self._use_canvas_engine,
            on_unavailable=self._record_renderer_reason,
            on_frame=self._rate_counter.record_frame,
        )
        if self._engine_gl is not None:
            self._engine_canvas.grid_remove()
            self._engine_gl.grid(row=0, column=0, sticky="nsew", padx=2, pady=(5, 2))
        self._fps_label = EcuRateLabel(
            engine,
            counter=self._rate_counter,
            theme=self._theme,
        )
        self._fps_label.place(relx=1.0, x=-8, y=9, anchor="ne")
        self._fps_label.lift()
        self._engine_summary = tk.Label(
            engine,
            text="--",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", FONT_CONTROL, "bold"),
            pady=7,
        )
        self._engine_summary.grid(row=1, column=0, sticky="ew", padx=5, pady=(2, 5))
        self._engine_summary.bind(
            "<Configure>",
            lambda event: self._engine_summary.configure(wraplength=max(1, event.width - 10)),
        )

        output = tk.Frame(engine, bg=ui.surface)
        output.grid(row=2, column=0, sticky="ew", padx=5, pady=(0, 5))
        output.grid_columnconfigure((0, 1), weight=1, uniform="engine-output")
        self._engine_output_field(output, 0, "ecu_power", "HORSEPOWER")
        self._engine_output_field(output, 1, "ecu_torque", "TORQUE")

        self._animation_toggle = tk.Button(
            engine,
            text="Animation: On",
            command=lambda: self.set_engine_animation(not self._animation_enabled),
            bg=ui.surface_alt,
            fg=ui.text,
            activebackground=ui.surface,
            activeforeground=ui.text,
            highlightbackground=ui.border,
            font=("Sans", FONT_CONTROL, "bold"),
            bd=0,
            pady=9,
            highlightthickness=0,
            relief=tk.FLAT,
        )
        self._animation_toggle.grid(row=3, column=0, sticky="ew", padx=5, pady=(0, 5))

        self._renderer_status = tk.Label(
            engine,
            text="",
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", FONT_SMALL),
            pady=3,
        )
        self._renderer_status.grid(row=4, column=0, sticky="ew", padx=5)
        self._renderer_status.bind(
            "<Configure>",
            lambda event: self._renderer_status.configure(wraplength=max(1, event.width - 10)),
        )
        self._record_renderer_reason(self._renderer_reason)

        # Keep telemetry cards outside the engine viewport so the complete
        # cutaway stays visible at every dashboard size.
        fuel = self._floating_card(
            cockpit,
            relx=0.005,
            rely=0.01,
            relwidth=0.35,
            relheight=0.475,
            icon="⛽",
            title="FUEL CONTROL",
            subtitle="Feedback and fuel correction",
            accent="#D6A800",
        )
        load = self._floating_card(
            cockpit,
            relx=0.005,
            rely=0.515,
            relwidth=0.35,
            relheight=0.475,
            icon="◆",
            title="ENGINE LOAD",
            subtitle="Demand, throttle and boost",
            accent="#D96A2B",
        )
        mixture = self._floating_card(
            cockpit,
            relx=0.645,
            rely=0.01,
            relwidth=0.35,
            relheight=0.475,
            icon="λ",
            title="MIXTURE",
            subtitle="Commanded vs. measured lambda",
            accent=ui.accent_primary,
        )
        ignition = self._floating_card(
            cockpit,
            relx=0.645,
            rely=0.515,
            relwidth=0.35,
            relheight=0.475,
            icon="ϟ",
            title="IGNITION",
            subtitle="Spark timing reported by ECU",
            accent=ui.accent_success,
        )
        self._build_fuel(fuel)
        self._build_load(load)
        self._build_mixture(mixture)
        self._build_ignition(ignition)

    def _floating_card(
        self,
        parent: tk.Misc,
        *,
        relx: float,
        rely: float,
        relwidth: float,
        relheight: float,
        icon: str,
        title: str,
        subtitle: str,
        accent: str,
    ) -> tk.Frame:
        ui = self._theme.ui
        card = tk.Frame(parent, bg=ui.surface, highlightthickness=1, highlightbackground=accent)
        card.place(relx=relx, rely=rely, relwidth=relwidth, relheight=relheight)
        card.lift()
        tk.Frame(card, bg=accent, width=3).grid(row=0, column=0, rowspan=3, sticky="nsw")
        card.grid_columnconfigure(1, weight=1)
        card.grid_rowconfigure(2, weight=1)
        tk.Label(card, text=icon, fg=accent, bg=ui.surface, font=("Sans", 18, "bold")).grid(
            row=0, column=0, rowspan=2, sticky="n", padx=(9, 6), pady=(7, 0)
        )
        tk.Label(
            card, text=title, fg=accent, bg=ui.surface, font=("Sans", 13, "bold"), anchor="w"
        ).grid(row=0, column=1, sticky="ew", pady=(6, 0))
        tk.Label(
            card,
            text=subtitle,
            fg=ui.text_muted,
            bg=ui.surface,
            font=("Sans", FONT_SMALL),
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(0, 5))
        body = tk.Frame(card, bg=ui.surface)
        body.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=9, pady=(1, 5))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_columnconfigure(2, weight=2)
        body.bind("<Configure>", lambda event: self._fit_card(body, event.width))
        return body

    def _fit_card(self, body: tk.Frame, width: int) -> None:
        fit_ecu_card(
            body, width, field_labels=self._field_labels, labels=self._labels, bars=self._bars
        )

    def _engine_output_field(
        self,
        parent: tk.Misc,
        column: int,
        key: str,
        title: str,
    ) -> None:
        ui = self._theme.ui
        field = tk.Frame(parent, bg=ui.surface_alt)
        field.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=(0, 2) if column == 0 else (2, 0),
        )
        tk.Label(
            field,
            text=title,
            fg=ui.text_muted,
            bg=ui.surface_alt,
            font=("Sans", FONT_SMALL, "bold"),
        ).pack(fill="x", padx=4, pady=(3, 0))
        value = tk.Label(
            field,
            text="--",
            fg=ui.accent_primary,
            bg=ui.surface_alt,
            font=("Sans", FONT_BODY, "bold"),
        )
        value.pack(fill="x", padx=4, pady=(0, 3))
        self._labels[key] = value

    def _value(
        self, parent: tk.Misc, row: int, key: str, label: str, *, status: bool = False
    ) -> None:
        ui = self._theme.ui
        field = tk.Label(
            parent, text=label, fg=ui.text, bg=ui.surface, font=("Sans", FONT_SMALL), anchor="w"
        )
        field.grid(row=row, column=0, sticky="w", pady=2)
        field._full_text = label
        self._field_labels[key] = field
        value = tk.Label(
            parent,
            text="--",
            fg=ui.accent_primary if not status else ui.accent_success,
            bg=ui.surface,
            font=("Sans", FONT_BODY, "bold"),
            anchor="e",
        )
        value.grid(row=row, column=1, sticky="e", padx=(3, 6), pady=2)
        self._labels[key] = value

    def _bar(self, parent: tk.Misc, row: int, key: str, *, height: int = 24) -> None:
        ui = self._theme.ui
        canvas = tk.Canvas(
            parent, width=1, height=max(height, 30), bg=ui.surface, highlightthickness=0, bd=0
        )
        canvas.grid(row=row, column=2, sticky="ew", pady=3)
        canvas.bind("<Configure>", lambda _e: self._paint_bars())
        self._bars[key] = canvas

    def _build_fuel(self, body: tk.Frame) -> None:
        ui = self._theme.ui
        mode = tk.Label(
            body, text="--", fg=ui.text, bg=ui.surface, font=("Sans", 15, "bold"), anchor="w"
        )
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["fuel_mode"] = mode
        self._value(body, 1, "stft", "STFT (B1)")
        self._bar(body, 1, "stft")
        self._value(body, 2, "ltft", "LTFT (B1)")
        self._bar(body, 2, "ltft")
        self._value(body, 3, "fuel_status", "Fuel System", status=True)
        self._labels["fuel_status"].grid(columnspan=2, sticky="w")

    def _build_mixture(self, body: tk.Frame) -> None:
        mode = tk.Label(
            body,
            text="--",
            fg=self._theme.ui.text,
            bg=self._theme.ui.surface,
            font=("Sans", 15, "bold"),
            anchor="w",
        )
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["mixture_mode"] = mode
        self._value(body, 1, "commanded", "Commanded λ")
        self._bar(body, 1, "commanded")
        self._value(body, 2, "measured", "Measured λ")
        self._bar(body, 2, "measured")
        self._value(body, 3, "mixture_status", "Tracking", status=True)
        self._labels["mixture_status"].grid(columnspan=2, sticky="w")

    def _build_load(self, body: tk.Frame) -> None:
        mode = tk.Label(
            body,
            text="--",
            fg=self._theme.ui.text,
            bg=self._theme.ui.surface,
            font=("Sans", 15, "bold"),
            anchor="w",
        )
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["load_mode"] = mode
        self._value(
            body,
            1,
            "load",
            "Calculated Load"
            if self._vehicle_state.engine_load_percent is not None
            else "Absolute Load",
        )
        self._bar(body, 1, "load")
        self._value(body, 2, "boost", "Boost Pressure")
        self._bar(body, 2, "boost")
        self._value(body, 3, "throttle", "Throttle")
        self._bar(body, 3, "throttle")

    def _build_ignition(self, body: tk.Frame) -> None:
        mode = tk.Label(
            body,
            text="--",
            fg=self._theme.ui.text,
            bg=self._theme.ui.surface,
            font=("Sans", 15, "bold"),
            anchor="w",
        )
        mode.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(1, 7))
        self._labels["ignition_mode"] = mode
        self._value(body, 1, "timing", "Timing Advance")
        self._bar(body, 1, "timing")
        self._value(body, 2, "ignition_status", "Timing Data", status=True)
        self._labels["ignition_status"].grid(columnspan=2, sticky="w")
