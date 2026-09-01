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

    _TABS = ("PERFORMANCE", "ENGINE", "OFF-ROAD", "TRIP")
    _GAUGE_VIEWS: dict[str, tuple[tuple[str, ...], int]] = {
        # Gear will join this group once the learned-ratio estimator is wired in.
        "PERFORMANCE": (("rpm", "boost", "speed", "throttle"), 4),
        # Engine and vehicle-health telemetry share one page. Five compact linear
        # gauges use the available area much better than two mostly empty tabs.
        "ENGINE": (("coolant", "intake", "load", "fuel", "voltage"), 3),
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
        self._view_content: tk.Widget | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        tabs = tk.Frame(self, bg=BG)
        tabs.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        for column, name in enumerate(self._TABS):
            tabs.grid_columnconfigure(column, weight=1)
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
                pady=5,
            )
            button.grid(row=0, column=column, sticky="ew", padx=(0, 4))
            self._view_buttons[name] = button

        self._view_host = tk.Frame(self, bg=BG)
        self._view_host.grid(row=1, column=0, sticky="nsew")
        self._view_host.grid_columnconfigure(0, weight=1)
        self._view_host.grid_rowconfigure(0, weight=1)

        self._show_view(self._current_view)

    def _show_view(self, name: str) -> None:
        """Switch the automotive dashboard to one telemetry group."""
        if name not in self._TABS:
            raise ValueError(f"Unknown vehicle view: {name}")

        self._current_view = name
        for view_name, button in self._view_buttons.items():
            active = view_name == name
            button.configure(
                bg=TAB_ACTIVE if active else TAB_BG,
                fg=TEXT if active else MUTED,
            )

        if self._view_content is not None:
            self._view_content.destroy()
        self._view_content = None
        self._gauges = None

        if name in self._GAUGE_VIEWS:
            self._show_gauges(name)
        elif name == "OFF-ROAD":
            self._show_placeholder(
                "OFF-ROAD",
                "Heading, pitch, roll, position and trail telemetry will live here.",
            )
        else:
            self._show_placeholder(
                "TRIP",
                "Trip distance, time, economy and drive statistics will live here.",
            )

    def _show_gauges(self, name: str) -> None:
        visible_ids, columns = self._GAUGE_VIEWS[name]
        definitions = tuple(
            definition
            for definition in DEFAULT_GAUGES
            if definition.gauge_id in visible_ids
        )
        panel = VehicleGaugePanel(
            self._view_host,
            definitions=definitions,
            columns=columns,
            show_config_button=False,
        )
        panel.grid(row=0, column=0, sticky="nsew")

        # orcUi already provides the surrounding shell and navigation. The
        # reusable panel's standalone connection toolbar is redundant here.
        panel._toolbar.grid_remove()  # type: ignore[attr-defined]
        self._gauges = panel
        self._view_content = panel
        self._apply_state()

    def _show_placeholder(self, title: str, detail: str) -> None:
        frame = tk.Frame(self._view_host, bg=BG)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        body = tk.Frame(frame, bg="#0b1117", highlightthickness=1, highlightbackground="#25313b")
        body.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        tk.Label(body, text=title, fg=TEXT, bg="#0b1117", font=("Sans", 22, "bold")).pack(pady=(80, 10))
        tk.Label(body, text=detail, fg=MUTED, bg="#0b1117", font=("Sans", 11)).pack()
        self._view_content = frame

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
