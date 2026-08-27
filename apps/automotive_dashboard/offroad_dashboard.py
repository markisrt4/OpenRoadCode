# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone composition for the reusable Tk off-road dashboard panel."""

from __future__ import annotations

import argparse
import math
import tkinter as tk

from apps.automotive_dashboard.navigation_bus_state import (
    NavigationBusSnapshot,
    NavigationBusState,
)
from frontends.tk.automotive import OffroadDashboardPanel
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    MOTION_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
    decode_motion_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from services.navigation.zeromq_navigation_command_server import (
    DEFAULT_NAVIGATION_COMMAND_ENDPOINT,
)
from services.navigation.zeromq_navigation_request_handler import (
    ZeroMqNavigationRequestHandler,
)
from ui.navigation import HeadingReference, PositionFix
from ui.system import StatusMessage, StatusSeverity


class OffroadDashboardApp:
    """Present public navigation telemetry and forward navigation commands."""

    def __init__(
        self,
        state: NavigationBusState,
        commands: ZeroMqNavigationRequestHandler,
        update_ms: int,
        pitch_warning_deg: float,
        roll_warning_deg: float,
        calibrate_on_start: bool,
        gps_enabled: bool,
    ) -> None:
        self._state = state
        self._commands = commands
        self._update_ms = update_ms
        self._calibrate_on_start = calibrate_on_start
        self._calibration_requested = False
        self._gps_enabled = gps_enabled
        self._closed = False

        self._root = tk.Tk()
        self._root.title("OpenRoadCode Off-Road Dashboard")
        self._root.geometry("1024x600")
        self._root.minsize(760, 480)
        self._panel = OffroadDashboardPanel(
            self._root,
            pitch_warning_deg=pitch_warning_deg,
            roll_warning_deg=roll_warning_deg,
            request_handler=self,
        )
        self._panel.pack(fill=tk.BOTH, expand=True)

        self._root.protocol("WM_DELETE_WINDOW", self.close)
        self._root.bind("<Escape>", lambda _event: self.close())
        self._root.bind("q", lambda _event: self.close())
        self._root.bind("c", lambda _event: self.request_stationary_calibration())
        self._root.bind("h", lambda _event: self.request_heading_reset())

    def run(self) -> None:
        """Run the standalone Tk event loop."""
        self._root.after(0, self._poll)
        self._root.mainloop()

    def request_stationary_calibration(self) -> None:
        """Request stationary calibration from the navigation service."""
        self._panel.set_status("Calibrating · keep vehicle still")
        self._root.update_idletasks()
        try:
            self._commands.request_stationary_calibration()
        except Exception as exc:
            self._panel.set_status(
                StatusMessage(
                    "Calibration error",
                    StatusSeverity.ERROR,
                    str(exc),
                    "navigation",
                )
            )
        else:
            self._panel.set_status("Stationary calibration complete")

    def request_heading_reset(self) -> None:
        """Request a relative-heading reset from the navigation service."""
        try:
            self._commands.request_heading_reset()
        except Exception as exc:
            self._panel.set_status(
                StatusMessage(
                    "Heading reset error",
                    StatusSeverity.ERROR,
                    str(exc),
                    "navigation",
                )
            )
        else:
            self._panel.set_status("Relative heading zeroed")

    def close(self) -> None:
        """Destroy the standalone window."""
        if self._closed:
            return
        self._closed = True
        self._root.destroy()

    def _poll(self) -> None:
        if self._closed:
            return

        state = self._state.snapshot()
        if state.connected:
            self._present_state(state)
            if self._calibrate_on_start and not self._calibration_requested:
                self._calibration_requested = True
                self._root.after(0, self.request_stationary_calibration)
        elif state.error is not None:
            self._panel.set_status(
                StatusMessage(
                    "Navigation error",
                    StatusSeverity.ERROR,
                    state.error,
                    "navigation",
                )
            )
        else:
            self._panel.set_status(state.status)

        self._root.after(self._update_ms, self._poll)

    def _present_state(self, state: NavigationBusSnapshot) -> None:
        heading = state.heading_deg or 0.0
        pitch = state.pitch_deg or 0.0
        roll = state.roll_deg or 0.0

        self._panel.set_heading(math.radians(heading), HeadingReference.RELATIVE)
        self._panel.set_pitch(math.radians(pitch))
        self._panel.set_roll(math.radians(roll))

        linear = state.linear_acceleration_mps2
        if linear is not None:
            self._panel.set_accel_x(linear.x)
            self._panel.set_accel_y(linear.y)
            self._panel.set_accel_z(linear.z)
            self._panel.set_accel_total(
                math.sqrt(linear.x**2 + linear.y**2 + linear.z**2)
            )

        gps = state.gps
        if (
            gps is not None
            and gps.has_fix
            and gps.latitude_deg is not None
            and gps.longitude_deg is not None
        ):
            self._panel.set_position(
                PositionFix(
                    latitude_rad=math.radians(gps.latitude_deg),
                    longitude_rad=math.radians(gps.longitude_deg),
                    altitude_m=gps.altitude_m,
                    pfom_m=gps.accuracy_m,
                )
            )
            self._panel.set_ground_speed(gps.speed_mps)
            self._panel.set_course_over_ground(
                math.radians(gps.course_deg)
                if gps.course_deg is not None
                else None
            )
        else:
            self._panel.set_position(None)
            self._panel.set_ground_speed(None)
            self._panel.set_course_over_ground(None)

        self._panel.set_status(self._status_for(state))

    def _status_for(self, state: NavigationBusSnapshot) -> str:
        pitch = state.pitch_deg or 0.0
        roll = state.roll_deg or 0.0
        if abs(roll) >= 120.0 or abs(pitch) >= 120.0:
            return "Capsized · call the winch crew first"
        if self._gps_enabled and state.gps is None:
            return "Navigation online · waiting for GPS telemetry"
        if self._gps_enabled and not state.gps.has_fix:
            return "Navigation online · acquiring GPS"
        return state.status


def parse_args() -> argparse.Namespace:
    """Parse and validate standalone dashboard command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Display a trail-oriented off-road vehicle dashboard."
    )
    parser.add_argument("--endpoint", default=LOCAL_SUBSCRIBER_ENDPOINT)
    parser.add_argument("--command-endpoint", default=DEFAULT_NAVIGATION_COMMAND_ENDPOINT)
    parser.add_argument("--update-ms", type=int, default=75)
    parser.add_argument("--pitch-warning", type=float, default=30.0)
    parser.add_argument("--roll-warning", type=float, default=25.0)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument(
        "--gps",
        action="store_true",
        help="Show GPS acquisition status; GPS hardware is owned by the navigation service",
    )
    args = parser.parse_args()

    if args.update_ms <= 0:
        parser.error("--update-ms must be greater than zero")
    if args.pitch_warning <= 0 or args.roll_warning <= 0:
        parser.error("warning angles must be greater than zero")
    return args


def _build_dispatcher(endpoint: str, state: NavigationBusState) -> MessageDispatcher:
    dispatcher = MessageDispatcher(ZeroMqSubscriber(endpoint), error_handler=state.set_error)
    dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, state.set_attitude)
    dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, state.set_imu)
    dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, state.set_position)
    dispatcher.register(MOTION_STATE_TOPIC, decode_motion_state, state.set_motion)
    return dispatcher


def main() -> int:
    """Construct bus dependencies and run the standalone off-road dashboard."""
    args = parse_args()
    state = NavigationBusState()
    dispatcher = _build_dispatcher(args.endpoint, state)
    commands = ZeroMqNavigationRequestHandler(args.command_endpoint)
    app = OffroadDashboardApp(
        state=state,
        commands=commands,
        update_ms=args.update_ms,
        pitch_warning_deg=args.pitch_warning,
        roll_warning_deg=args.roll_warning,
        calibrate_on_start=args.calibrate,
        gps_enabled=args.gps,
    )
    dispatcher.start()
    try:
        app.run()
    finally:
        commands.close()
        dispatcher.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
