# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Full-screen vehicle telemetry panel for orcUi."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from types import SimpleNamespace

from apps.orcUi.vehicle_presenter import VehiclePresentationState
from frontends.tk.automotive import DEFAULT_GAUGES, VehicleGaugePanel


class VehiclePanel(tk.Frame):
    """ORC vehicle dashboard backed by the reusable automotive gauges."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_back: Callable[[], None],
        state: VehiclePresentationState | None = None,
    ) -> None:
        super().__init__(parent, bg="#000000")
        self._state = state or VehiclePresentationState()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = tk.Frame(self, bg="#000000")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        tk.Button(
            header,
            text="‹ HOME",
            command=on_back,
            bg="#101820",
            fg="#edf2f5",
            activebackground="#17232d",
            activeforeground="#edf2f5",
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 10, "bold"),
            padx=14,
            pady=6,
        ).pack(side=tk.LEFT)
        tk.Label(
            header,
            text="VEHICLE",
            fg="#84ce1f",
            bg="#000000",
            font=("Sans", 13, "bold"),
        ).pack(side=tk.LEFT, padx=14)
        tk.Label(
            header,
            text="LIVE TELEMETRY",
            fg="#89959e",
            bg="#000000",
            font=("Monospace", 9),
        ).pack(side=tk.RIGHT, padx=4)

        # Start with the gauges ORC can populate from today's VehicleState
        # contract. More definitions can be enabled as the contract grows.
        visible_ids = {
            "rpm",
            "boost",
            "speed",
            "throttle",
            "coolant",
            "intake",
            "load",
            "voltage",
            "fuel",
        }
        definitions = tuple(
            definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in visible_ids
        )
        self._gauges = VehicleGaugePanel(
            self,
            definitions=definitions,
            columns=4,
            show_config_button=False,
        )
        self._gauges.grid(row=1, column=0, sticky="nsew")

        self.update_state(self._state)

    def update_state(self, state: VehiclePresentationState) -> None:
        """Refresh the performance gauges from the latest ORC vehicle state."""
        self._state = state
        gauge_state = SimpleNamespace(
            rpm=state.engine_speed_rpm,
            speed_mph=state.speed_mph,
            boost_psi=state.boost_psi,
            throttle_pct=state.throttle_percent,
            coolant_temp_f=state.coolant_temperature_f,
            intake_temp_f=state.intake_air_temperature_f,
            engine_load_pct=state.engine_load_percent,
            control_voltage=state.control_voltage_v,
            fuel_level_pct=state.fuel_percent,
        )
        self._gauges.update_state(gauge_state, connected=True)
