# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Car UI destination hosting the reusable Tk off-road dashboard."""

from __future__ import annotations

import math
import tkinter as tk

from controllers.navigation.map_presentation_if import MapPresentationIf
from frontends.tk.automotive import OffroadDashboardPanel
from frontends.tk.tk_screen_host_if import TkScreenHostIf
from messaging.contracts.navigation import (
    AttitudeStateMessage,
    ImuStateMessage,
    MotionStateMessage,
    PositionStateMessage,
)
from ui.navigation import HeadingReference, NavigationRequestHandlerIf, PositionFix
from ui.screen_ui_if import ScreenId
from ui.system import StatusMessage, StatusSeverity

from apps.carUi.screens.car_ui_screen import CarUiScreen
from apps.carUi.screens.car_ui_screen_services import MenuTileFactory


class OffroadDashboardScreen(CarUiScreen):
    """Render public navigation telemetry without owning navigation hardware."""

    def __init__(
        self,
        host: TkScreenHostIf,
        *,
        create_menu_tile: MenuTileFactory,
        back_action,
        request_handler: NavigationRequestHandlerIf | None = None,
        map_presentation: MapPresentationIf | None = None,
        pitch_warning_deg: float = 30.0,
        roll_warning_deg: float = 25.0,
    ) -> None:
        super().__init__(host, ScreenId("offroad_dashboard"), create_menu_tile)
        self._back_action = back_action
        self._request_handler = request_handler
        self._map_presentation = map_presentation
        self._pitch_warning_deg = pitch_warning_deg
        self._roll_warning_deg = roll_warning_deg
        self._panel: OffroadDashboardPanel | None = None
        self._latest_position: PositionFix | None = None
        self._attitude_count = 0
        self._imu_count = 0
        self._position_count = 0
        self._motion_count = 0

    def show(self) -> None:
        """Build the panel and display the latest bus-fed state."""
        self.prepare_screen("Off-Road", self._back_action)
        self._panel = OffroadDashboardPanel(
            self.content_frame,
            pitch_warning_deg=self._pitch_warning_deg,
            roll_warning_deg=self._roll_warning_deg,
            request_handler=self._request_handler,
        )
        self._panel.pack(fill="both", expand=True)
        if self._map_presentation is not None:
            tk.Button(
                self._panel,
                text="GOOGLE EARTH",
                command=self.show_current_location_on_map,
                bg="#263d31",
                fg="#e5f2e9",
                activebackground="#355442",
                activeforeground="#ffffff",
                relief=tk.FLAT,
                padx=14,
                font=("TkDefaultFont", 9, "bold"),
            ).pack(side=tk.BOTTOM, padx=10, pady=(0, 7), anchor="w")
        self._set_live_status()

    def hide(self) -> None:
        """Release only the view; telemetry ownership remains outside the screen."""
        self._panel = None

    def show_current_location_on_map(self) -> None:
        """Present the latest navigation fix using the configured map backend."""
        presentation = self._map_presentation
        position = self._latest_position
        if presentation is None:
            self.set_status("Map presentation unavailable")
            return
        if position is None:
            self.set_status("Waiting for a GPS position")
            return
        presentation.focus_location(
            math.degrees(position.latitude_rad),
            math.degrees(position.longitude_rad),
            altitude_m=position.altitude_m,
        )
        self.set_status("Opening current location")

    def set_attitude_message(self, message: AttitudeStateMessage) -> None:
        """Apply one decoded attitude message to the visible panel."""
        self._attitude_count += 1
        panel = self._panel
        if panel is None:
            return
        panel.set_heading(message.data.heading_rad, HeadingReference.RELATIVE)
        panel.set_pitch(message.data.pitch_rad)
        panel.set_roll(message.data.roll_rad)
        self._set_live_status()

    def set_imu_message(self, message: ImuStateMessage) -> None:
        """Apply linear acceleration from one decoded IMU message."""
        self._imu_count += 1
        panel = self._panel
        if panel is None:
            return
        linear = message.data.linear_acceleration_m_s2
        panel.set_accel_x(linear.x)
        panel.set_accel_y(linear.y)
        panel.set_accel_z(linear.z)
        panel.set_accel_total(math.sqrt(linear.x**2 + linear.y**2 + linear.z**2))
        self._set_live_status()

    def set_position_message(self, message: PositionStateMessage) -> None:
        """Apply decoded geographic position and ground-track data."""
        self._position_count += 1
        data = message.data
        if data.latitude_rad is None or data.longitude_rad is None:
            self._latest_position = None
        else:
            self._latest_position = PositionFix(
                latitude_rad=data.latitude_rad,
                longitude_rad=data.longitude_rad,
                altitude_m=data.altitude_m,
                pfom_m=data.accuracy_m,
            )

        panel = self._panel
        if panel is None:
            return
        panel.set_position(self._latest_position)
        panel.set_ground_speed(data.speed_m_s)
        panel.set_course_over_ground(data.course_rad)
        self._set_live_status()

    def set_motion_message(self, message: MotionStateMessage) -> None:
        """Apply decoded derived motion values used by the panel."""
        self._motion_count += 1
        panel = self._panel
        if panel is None:
            return
        panel.set_rate_of_climb(message.data.vertical_speed_m_s)
        self._set_live_status()

    def set_navigation_error(self, topic: str, error: Exception) -> None:
        """Expose a navigation bus or decode failure on the visible panel."""
        panel = self._panel
        text = f"Navigation error [{topic}]: {type(error).__name__}"
        if panel is not None:
            panel.set_status(
                StatusMessage(text, StatusSeverity.ERROR, source="navigation")
            )
        self.set_status(text)

    def _set_live_status(self) -> None:
        panel = self._panel
        if panel is None:
            return
        if self._attitude_count == 0 and self._imu_count == 0:
            status = "Waiting for navigation telemetry"
        else:
            status = (
                "Navigation bus online · "
                f"att {self._attitude_count} · imu {self._imu_count} · "
                f"pos {self._position_count} · motion {self._motion_count}"
            )
        panel.set_status(status)
        self.set_status(status)
