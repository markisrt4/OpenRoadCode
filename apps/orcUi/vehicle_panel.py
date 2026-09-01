# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full-screen vehicle telemetry panel for orcUi."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from types import SimpleNamespace

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import DEFAULT_GAUGES, VehicleGaugePanel


BG = "#000000"
TAB_BG = "#101820"
TAB_ACTIVE = "#168bd1"
TEXT = "#edf2f5"
MUTED = "#89959e"


class VehiclePanel(tk.Frame):
    """ORC vehicle dashboard backed by the reusable automotive gauges."""

    _VIEWS: dict[str, tuple[tuple[str, ...], int]] = {
        "PERFORMANCE": (("rpm", "boost", "speed", "throttle"), 4),
        "ENGINE": (("coolant", "intake", "load"), 3),
        "VEHICLE": (("fuel", "voltage"), 2),
    }

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        state: VehiclePresentationState | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        # The shell already owns navigation, including Home. Keep the argument
        # for the existing panel contract but do not duplicate that control here.
        self._on_back = on_back
        self._state = state or VehiclePresentationState()
        self._current_view = "PERFORMANCE"
        self._view_buttons: dict[str, tk.Button] = {}
        self._gauges: VehicleGaugePanel | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        tabs = tk.Frame(self, bg=BG)
        tabs.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        for name in self._VIEWS:
            button = tk.Button(
                tabs,
                text=name,
                command=lambda selected=name: self._show_view(selected),
                bg=TAB_BG,
                fg=TEXT,
                activebackground=TAB_ACTIVE,
                activeforeground=TEXT,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9, "bold"),
                padx=18,
                pady=5,
            )
            button.pack(side=tk.LEFT, padx=(0, 4))
            self._view_buttons[name] = button

        self._gauge_host = tk.Frame(self, bg=BG)
        self._gauge_host.grid(row=1, column=0, sticky="nsew")
        self._gauge_host.grid_columnconfigure(0, weight=1)
        self._gauge_host.grid_rowconfigure(0, weight=1)

        self._show_view(self._current_view)

    def _show_view(self, name: str) -> None:
        """Switch the automotive dashboard to one telemetry group."""
        if name not in self._VIEWS:
            raise ValueError(f"Unknown vehicle view: {name}")

        self._current_view = name
        for view_name, button in self._view_buttons.items():
            active = view_name == name
            button.configure(
                bg=TAB_ACTIVE if active else TAB_BG,
                fg=TEXT if active else MUTED,
            )

        if self._gauges is not None:
            self._gauges.destroy()

        visible_ids, columns = self._VIEWS[name]
        definitions = tuple(
            definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in visible_ids
        )
        self._gauges = VehicleGaugePanel(
            self._gauge_host,
            definitions=definitions,
            columns=columns,
            show_config_button=False,
        )
        self._gauges.grid(row=0, column=0, sticky="nsew")

        # orcUi already provides the surrounding shell and navigation. The
        # reusable panel's standalone connection toolbar is redundant here.
        self._gauges._toolbar.grid_remove()  # type: ignore[attr-defined]
        self._apply_state()

    def update_state(self, state: VehiclePresentationState) -> None:
        """Refresh the visible automotive gauges from the latest ORC state."""
        self._state = state
        self._apply_state()

    def _apply_state(self) -> None:
        if self._gauges is None:
            return
        gauge_state = SimpleNamespace(
            rpm=self._state.engine_speed_rpm,
            speed_mph=self._state.speed_mph,
            boost_psi=self._state.boost_psi,
            throttle_pct=self._state.throttle_percent,
            coolant_temp_f=self._state.coolant_temperature_f,
            intake_temp_f=self._state.intake_air_temperature_f,
            engine_load_pct=self._state.engine_load_percent,
            control_voltage=self._state.control_voltage_v,
            fuel_level_pct=self._state.fuel_percent,
        )
        self._gauges.update_state(gauge_state, connected=True)
