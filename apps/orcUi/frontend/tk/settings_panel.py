# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from controllers.automotive import EngineInductionType, VehicleConfiguration
from ui.theme import ThemeBundle, ThemeMode


class SettingsPanel(tk.Frame):
    """Top-level OpenRoadCode settings surface."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        vehicle_configuration: VehicleConfiguration,
        on_vehicle_configuration_changed: Callable[[VehicleConfiguration], None],
        on_back: Callable[[], None],
        theme_bundle: ThemeBundle | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle or packaged_theme_bundle(ThemeMode.DARK)
        ui = self._theme_bundle.ui
        super().__init__(parent, bg=ui.background)
        self._on_changed = on_vehicle_configuration_changed
        self._on_back = on_back
        self._vehicle_configuration = vehicle_configuration
        self._induction_var = tk.StringVar(value=vehicle_configuration.induction.value)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(
            self,
            bg=ui.surface_alt,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        header.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 8))
        tk.Label(
            header,
            text="SETTINGS",
            bg=ui.surface_alt,
            fg=ui.text,
            font=("Sans", 18, "bold"),
        ).pack(side=tk.LEFT, padx=14, pady=10)
        tk.Button(
            header,
            text="BACK",
            command=self._on_back,
            bg=ui.control_background,
            fg=ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 9, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.RIGHT, padx=10, pady=8)

        body = tk.Frame(self, bg=ui.background)
        body.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        body.grid_columnconfigure(0, weight=1)

        vehicle = tk.Frame(
            body,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        vehicle.grid(row=0, column=0, sticky="ew", pady=4)
        vehicle.grid_columnconfigure(1, weight=1)

        tk.Label(
            vehicle,
            text="VEHICLE",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 3))
        tk.Label(
            vehicle,
            text="Engine induction",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", 12, "bold"),
        ).grid(row=1, column=0, sticky="nw", padx=14, pady=(8, 2))
        tk.Label(
            vehicle,
            text="Controls boost/vacuum presentation and forced-induction analysis.",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", 8),
            justify=tk.LEFT,
        ).grid(row=2, column=0, sticky="nw", padx=14, pady=(0, 12))

        choices = tk.Frame(vehicle, bg=ui.surface)
        choices.grid(row=1, column=1, rowspan=2, sticky="e", padx=14, pady=10)

        for row, induction in enumerate(EngineInductionType):
            tk.Radiobutton(
                choices,
                text=induction.display_name,
                variable=self._induction_var,
                value=induction.value,
                command=self._apply_induction,
                bg=ui.surface,
                fg=ui.text,
                activebackground=ui.surface,
                activeforeground=ui.text,
                selectcolor=ui.control_background,
                font=("Sans", 9),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", pady=2)

    @property
    def vehicle_configuration(self) -> VehicleConfiguration:
        return self._vehicle_configuration

    def _apply_induction(self) -> None:
        configuration = VehicleConfiguration(
            induction=EngineInductionType(self._induction_var.get())
        )
        self._vehicle_configuration = configuration
        self._on_changed(configuration)
