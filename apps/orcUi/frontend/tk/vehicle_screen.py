# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Vehicle-screen lifecycle for the integrated orcUi Tk frontend."""

from __future__ import annotations

from collections.abc import Callable

from apps.orcUi.frontend.tk.presentation_state import OrcUiPresentationState
from controllers.automotive import (
    AutomotiveTelemetryProfile,
    VehicleConfiguration,
)
from frontends.tk.tk_screen import TkScreen
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from ui.screen_ui_if import ScreenId
from ui.theme import ThemeBundle

from .screen_builders import build_vehicle_screen
from .vehicle_panel import VehiclePanel


class VehicleScreen(TkScreen):
    """Own the VEHICLE destination and its transient dashboard presentation."""

    SCREEN_ID = ScreenId("VEHICLE")

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        theme_bundle: Callable[[], ThemeBundle],
        presentation: OrcUiPresentationState,
        telemetry_profile_request: (
            Callable[[AutomotiveTelemetryProfile], None] | None
        ),
        vehicle_configuration: Callable[[], VehicleConfiguration],
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(self.SCREEN_ID)
        self._host = host
        self._theme_bundle = theme_bundle
        self._presentation = presentation
        self._telemetry_profile_request = telemetry_profile_request
        self._vehicle_configuration = vehicle_configuration
        self._on_back = on_back
        self._panel: VehiclePanel | None = None

    def show(self) -> None:
        """Build VEHICLE content from the latest presentation state."""
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title("VEHICLE")

        self._panel = build_vehicle_screen(
            self._host.screen_parent,
            on_back=self._on_back,
            on_view_changed=lambda view: self._host.set_screen_title(view),
            on_telemetry_profile=self._telemetry_profile_request,
            state=self._presentation.vehicle,
            trip_state=self._presentation.trip,
            theme=self._theme_bundle(),
            vehicle_configuration=self._vehicle_configuration(),
            engine_analysis=self._presentation.engine_analysis,
        )

    def hide(self) -> None:
        """Release VEHICLE telemetry demand when navigating away."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.release_telemetry_profile()
        self._panel = None

    def show_trip_view(self) -> None:
        """Switch the mounted VEHICLE destination directly to its trip view."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.show_trip_view()

    def apply_vehicle_state(self, state) -> None:
        """Refresh the mounted vehicle dashboard."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_state(state)

    def apply_trip_state(self, state) -> None:
        """Refresh the mounted trip presentation."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_trip_state(state)

    def apply_engine_analysis(self, analysis) -> None:
        """Refresh the mounted engine analysis."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_engine_analysis(analysis)

    def apply_position_state(self, state) -> None:
        """Refresh the mounted off-road position presentation."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_position(state)

    def apply_attitude_state(self, state) -> None:
        """Refresh the mounted off-road attitude presentation."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.update_attitude(state)

    def set_vehicle_configuration(
        self,
        configuration: VehicleConfiguration,
    ) -> None:
        """Refresh mounted instruments after vehicle configuration changes."""
        panel = self._panel
        if panel is not None and panel.winfo_exists():
            panel.set_vehicle_configuration(configuration)
