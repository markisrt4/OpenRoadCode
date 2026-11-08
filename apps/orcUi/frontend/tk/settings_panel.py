# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from apps.orcUi.theme_runtime import theme_bundle as packaged_theme_bundle
from common.units import UnitSystem
from ui.automotive.vehicle_configuration import (EngineInductionType, VehicleConfiguration)
from ui.theme import ThemeBundle, ThemeMode
from ui.navigation.host_location_ui_if import HostLocationRequestHandlerIf, HostLocationState
from .shell_metrics import FONT_BODY, FONT_CONTROL, FONT_SMALL
from ui.ui_widget import UiWidget


class SettingsPanel(tk.Frame, UiWidget):
    """Top-level OpenRoadCode settings surface."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        vehicle_configuration: VehicleConfiguration,
        on_vehicle_configuration_changed: Callable[[VehicleConfiguration], None],
        unit_system: UnitSystem,
        on_unit_system_changed: Callable[[UnitSystem], None],
        on_back: Callable[[], None],
        theme_bundle: ThemeBundle | None = None,
        host_location_handler: HostLocationRequestHandlerIf | None = None,
        host_location_state: HostLocationState = HostLocationState(),
        performance_overlay_enabled: Callable[[], bool] | None = None,
        on_performance_overlay_changed: Callable[[bool], None] | None = None,
    ) -> None:
        self._theme_bundle = theme_bundle or packaged_theme_bundle(ThemeMode.DARK)
        ui = self._theme_bundle.ui
        super().__init__(parent, bg=ui.background)
        self._on_changed = on_vehicle_configuration_changed
        self._on_unit_system_changed = on_unit_system_changed
        self._on_back = on_back
        self._vehicle_configuration = vehicle_configuration
        self._induction_var = tk.StringVar(value=vehicle_configuration.induction.value)
        self._unit_system = unit_system
        self._unit_system_var = tk.StringVar(value=unit_system.value)
        self._on_performance_overlay_changed = on_performance_overlay_changed
        self._performance_overlay_var = tk.BooleanVar(value=performance_overlay_enabled() if performance_overlay_enabled else False)

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
            font=("Sans", FONT_CONTROL, "bold"),
            padx=14,
            pady=6,
            highlightthickness=0,
        ).pack(side=tk.RIGHT, padx=10, pady=8)

        body = tk.Frame(self, bg=ui.background)
        body.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        body.grid_columnconfigure(0, weight=1)

        display = tk.Frame(
            body,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        display.grid(row=1, column=0, sticky="ew", pady=4)
        display.grid_columnconfigure(1, weight=1)

        tk.Label(
            display,
            text="DISPLAY",
            bg=ui.surface,
            fg=ui.accent_primary,
            font=("Sans", 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 3))
        tk.Label(
            display,
            text="Units",
            bg=ui.surface,
            fg=ui.text,
            font=("Sans", FONT_BODY + 1, "bold"),
        ).grid(row=1, column=0, sticky="nw", padx=14, pady=(8, 2))
        tk.Label(
            display,
            text="Sets the preferred units for weather and other ORC displays.",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", FONT_SMALL),
            justify=tk.LEFT,
        ).grid(row=2, column=0, sticky="nw", padx=14, pady=(0, 12))

        unit_choices = tk.Frame(display, bg=ui.surface)
        unit_choices.grid(row=1, column=1, rowspan=2, sticky="e", padx=14, pady=8)
        self._unit_buttons = {}
        for row, (label, choice) in enumerate(
            (("Imperial", UnitSystem.IMPERIAL), ("Metric", UnitSystem.METRIC))
        ):
            button = tk.Button(
                unit_choices, text=label, width=12, height=2,
                command=lambda value=choice: self._select_unit(value),
                font=("Sans", FONT_CONTROL, "bold"), bd=0, relief=tk.FLAT,
                activeforeground=ui.text,
            )
            button.grid(row=row, column=0, sticky="ew", pady=3)
            self._unit_buttons[choice.value] = button
        self._refresh_unit_buttons()

        if on_performance_overlay_changed is not None:
            tk.Label(display, text="Performance HUD", bg=ui.surface, fg=ui.text,
                     font=("Sans", FONT_BODY + 1, "bold")).grid(
                         row=3, column=0, sticky="w", padx=14, pady=(4, 2))
            tk.Label(display, text="Show CPU, GPU and RAM over other screens.",
                     bg=ui.surface, fg=ui.text_muted, font=("Sans", FONT_SMALL)).grid(
                         row=4, column=0, sticky="w", padx=14, pady=(0, 12))
            self._hud_button = tk.Button(
                display, width=12, height=2, bd=0, relief=tk.FLAT,
                font=("Sans", FONT_CONTROL, "bold"),
                command=self._toggle_hud,
            )
            self._hud_button.grid(row=3, column=1, rowspan=2, sticky="e", padx=14, pady=8)
            self._refresh_hud_button()

        vehicle = tk.Frame(
            body,
            bg=ui.surface,
            highlightthickness=1,
            highlightbackground=ui.border,
        )
        vehicle.grid(row=2, column=0, sticky="ew", pady=4)
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
            font=("Sans", FONT_BODY + 1, "bold"),
        ).grid(row=1, column=0, sticky="nw", padx=14, pady=(8, 2))
        tk.Label(
            vehicle,
            text="Controls boost/vacuum presentation and forced-induction analysis.",
            bg=ui.surface,
            fg=ui.text_muted,
            font=("Sans", FONT_SMALL),
            justify=tk.LEFT,
        ).grid(row=2, column=0, sticky="nw", padx=14, pady=(0, 12))

        choices = tk.Frame(vehicle, bg=ui.surface)
        choices.grid(row=1, column=1, rowspan=2, sticky="e", padx=14, pady=8)
        self._induction_buttons = {}
        for row, induction in enumerate(EngineInductionType):
            button = tk.Button(
                choices, text=induction.display_name, width=22, height=2,
                command=lambda value=induction: self._select_induction(value),
                font=("Sans", FONT_CONTROL, "bold"), bd=0, relief=tk.FLAT,
                activeforeground=ui.text,
            )
            button.grid(row=row, column=0, sticky="ew", pady=3)
            self._induction_buttons[induction.value] = button
        self._refresh_induction_buttons()

        location = tk.Frame(body, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        location.grid(row=0, column=0, sticky="ew", pady=4)
        location.grid_columnconfigure(0, weight=1)
        tk.Label(location, text="LOCATION", bg=ui.surface, fg=ui.accent_primary,
                 font=("Sans", 10, "bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(8, 2))
        self._location_status = tk.StringVar(value=host_location_state.status)
        status = tk.Label(location, textvariable=self._location_status, bg=ui.surface, fg=ui.text_muted,
                          font=("Sans", FONT_SMALL), justify=tk.LEFT, anchor="w", wraplength=200)
        status.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        status.bind("<Configure>", lambda event: self._update_location_wrap(status, event.width))
        self._location_handler = host_location_handler
        self._location_button = tk.Button(
            location, text="SHARE HOST LOCATION", command=self._share_host_location,
            bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active,
            relief=tk.FLAT, font=("Sans", FONT_CONTROL, "bold"), padx=10, pady=6)
        self._location_button.grid(row=0, column=1, rowspan=2, padx=14, pady=8)
        self.set_host_location_state(host_location_state)

    def _share_host_location(self) -> None:
        if self._location_handler is not None:
            self._location_handler.share_host_location()

    @staticmethod
    def _update_location_wrap(label: tk.Label, width: int) -> None:
        wraplength = max(80, width)
        # A wrap update can itself cause Configure events. Do not repeatedly
        # request geometry for an unchanged width, especially on narrow X11 hosts.
        if int(label.cget("wraplength")) != wraplength:
            label.configure(wraplength=wraplength)

    def set_host_location_state(self, state: HostLocationState) -> None:
        self._location_status.set(state.status)
        self._location_button.configure(state=tk.DISABLED if state.busy or not state.can_share
                                        or self._location_handler is None else tk.NORMAL)

    @property
    def vehicle_configuration(self) -> VehicleConfiguration:
        return self._vehicle_configuration

    @property
    def unit_system(self) -> UnitSystem:
        return self._unit_system

    def _style_choice(self, button: tk.Button, selected: bool) -> None:
        ui = self._theme_bundle.ui
        button.configure(
            bg=ui.accent_primary if selected else ui.control_background,
            fg="#ffffff" if selected else ui.control_text,
            activebackground=ui.control_active,
            activeforeground="#ffffff",
        )

    def _refresh_unit_buttons(self) -> None:
        for value, button in self._unit_buttons.items():
            self._style_choice(button, value == self._unit_system_var.get())

    def _select_unit(self, value: UnitSystem) -> None:
        self._unit_system_var.set(value.value)
        self._refresh_unit_buttons()
        self._apply_unit_system()

    def _refresh_induction_buttons(self) -> None:
        for value, button in self._induction_buttons.items():
            self._style_choice(button, value == self._induction_var.get())

    def _select_induction(self, value: EngineInductionType) -> None:
        self._induction_var.set(value.value)
        self._refresh_induction_buttons()
        self._apply_induction()

    def _refresh_hud_button(self) -> None:
        enabled = self._performance_overlay_var.get()
        self._hud_button.configure(text="ON" if enabled else "OFF")
        self._style_choice(self._hud_button, enabled)

    def _toggle_hud(self) -> None:
        enabled = not self._performance_overlay_var.get()
        self._performance_overlay_var.set(enabled)
        self._refresh_hud_button()
        if self._on_performance_overlay_changed is not None:
            self._on_performance_overlay_changed(enabled)

    def _apply_unit_system(self) -> None:
        unit_system = UnitSystem(self._unit_system_var.get())
        self._unit_system = unit_system
        self._on_unit_system_changed(unit_system)

    def _apply_induction(self) -> None:
        configuration = VehicleConfiguration(
            induction=EngineInductionType(self._induction_var.get())
        )
        self._vehicle_configuration = configuration
        self._on_changed(configuration)
