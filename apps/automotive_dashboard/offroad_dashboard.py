# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone composition for the reusable Tk off-road dashboard panel."""

from __future__ import annotations

import argparse
import tkinter as tk

from controllers.navigation import (
    GpsdNavigationAdapter,
    Mpu6050NavigationAdapter,
    NavigationController,
    NavigationState,
    NavigationStatePresenter,
)
from frontends.tk.automotive import OffroadDashboardPanel
from hardware_io.imu import Mpu6050Imu
from ui.navigation import (
    NavigationRequestHandlerIf,
)
from ui.system import StatusMessage, StatusSeverity


class OffroadDashboardApp(NavigationRequestHandlerIf):
    """Own navigation lifecycle and present samples through UI contracts."""

    def __init__(
        self,
        controller: NavigationController,
        update_ms: int,
        pitch_warning_deg: float,
        roll_warning_deg: float,
        calibrate_on_start: bool,
        calibration_samples: int,
        calibration_interval_s: float,
        gps_enabled: bool,
    ) -> None:
        self._controller = controller
        self._update_ms = update_ms
        self._calibrate_on_start = calibrate_on_start
        self._calibration_samples = calibration_samples
        self._calibration_interval_s = calibration_interval_s
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
        self._presenter = NavigationStatePresenter(
            orientation_ui=self._panel,
            translation_ui=self._panel,
            position_ui=self._panel,
            ground_track_ui=self._panel,
        )

        self._root.protocol("WM_DELETE_WINDOW", self.close)
        self._root.bind("<Escape>", lambda _event: self.close())
        self._root.bind("q", lambda _event: self.close())
        self._root.bind("c", lambda _event: self.request_stationary_calibration())
        self._root.bind("h", lambda _event: self.request_heading_reset())

    def run(self) -> None:
        """Start navigation and run the standalone Tk event loop."""
        try:
            self._controller.start()
        except Exception as exc:
            self._panel.set_status(
                StatusMessage(
                    "Sensor error",
                    StatusSeverity.ERROR,
                    str(exc),
                    "navigation",
                )
            )
        else:
            self._panel.set_status("Navigation online")
            if self._calibrate_on_start:
                self._root.after(150, self.request_stationary_calibration)
            self._root.after(0, self._poll)
        self._root.mainloop()

    def request_stationary_calibration(self) -> None:
        """Calibrate the navigation estimator while stationary."""
        if not self._controller.is_started:
            self._panel.set_status(
                StatusMessage("Sensor not connected", StatusSeverity.WARNING)
            )
            return
        self._panel.set_status("Calibrating · keep vehicle still")
        self._root.update_idletasks()
        try:
            result = self._controller.calibrate_stationary(
                sample_count=self._calibration_samples,
                sample_interval_s=self._calibration_interval_s,
            )
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
            self._panel.set_status(f"Calibrated · {result.sample_count} samples")

    def request_heading_reset(self) -> None:
        """Reset the controller's relative heading estimate."""
        if self._controller.is_started:
            self._controller.reset_heading()
            self._panel.set_status("Relative heading zeroed")

    def close(self) -> None:
        """Stop navigation and destroy the standalone window."""
        if self._closed:
            return
        self._closed = True
        self._controller.stop()
        self._root.destroy()

    def _poll(self) -> None:
        if self._closed or not self._controller.is_started:
            return
        try:
            state = self._controller.read_state()
        except Exception as exc:
            self._panel.set_status(
                StatusMessage(
                    "Navigation error",
                    StatusSeverity.ERROR,
                    str(exc),
                    "navigation",
                )
            )
            return

        self._present_state(state)
        self._root.after(self._update_ms, self._poll)

    def _present_state(self, state: NavigationState) -> None:
        self._presenter.present(state)
        self._panel.set_status(self._status_for(state))

    def _status_for(self, state: NavigationState) -> str:
        if abs(state.roll_deg) >= 120.0 or abs(state.pitch_deg) >= 120.0:
            return "Capsized · call the winch crew first"
        if self._gps_enabled and state.gps is None:
            return "IMU online · waiting for GPSD"
        if self._gps_enabled and not state.gps.has_fix:
            return "IMU online · acquiring GPS"
        if self._controller.calibration is None:
            return "Navigation online · calibration recommended"
        return "Navigation online · calibrated"


def parse_args() -> argparse.Namespace:
    """Parse and validate standalone dashboard command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Display a trail-oriented off-road vehicle dashboard."
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=Mpu6050Imu.DEFAULT_ADDRESS,
    )
    parser.add_argument("--update-ms", type=int, default=75)
    parser.add_argument("--filter-time-constant", type=float, default=0.5)
    parser.add_argument("--pitch-warning", type=float, default=30.0)
    parser.add_argument("--roll-warning", type=float, default=25.0)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--calibration-samples", type=int, default=100)
    parser.add_argument("--calibration-interval", type=float, default=0.01)
    parser.add_argument("--gps", action="store_true")
    parser.add_argument("--gps-host", default="127.0.0.1")
    parser.add_argument("--gps-port", default="2947")
    args = parser.parse_args()

    if args.update_ms <= 0:
        parser.error("--update-ms must be greater than zero")
    if args.filter_time_constant < 0:
        parser.error("--filter-time-constant must be zero or greater")
    if args.pitch_warning <= 0 or args.roll_warning <= 0:
        parser.error("warning angles must be greater than zero")
    if args.calibration_samples <= 0:
        parser.error("--calibration-samples must be greater than zero")
    if args.calibration_interval < 0:
        parser.error("--calibration-interval must be zero or greater")
    return args


def main() -> int:
    """Construct dependencies and run the standalone off-road dashboard."""
    args = parse_args()
    gps_source = None
    if args.gps:
        from hardware_io.gps import GpsReader

        gps_source = GpsdNavigationAdapter(
            GpsReader(host=args.gps_host, port=args.gps_port)
        )

    controller = NavigationController(
        sensor=Mpu6050NavigationAdapter(
            Mpu6050Imu(address=args.address)
        ),
        filter_time_constant_s=args.filter_time_constant,
        gps_source=gps_source,
    )
    app = OffroadDashboardApp(
        controller=controller,
        update_ms=args.update_ms,
        pitch_warning_deg=args.pitch_warning,
        roll_warning_deg=args.roll_warning,
        calibrate_on_start=args.calibrate,
        calibration_samples=args.calibration_samples,
        calibration_interval_s=args.calibration_interval,
        gps_enabled=args.gps,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
