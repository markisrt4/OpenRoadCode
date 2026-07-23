"""Tkinter wireframe vehicle visualizer for navigation state."""

from __future__ import annotations

import argparse
import math
import tkinter as tk
from dataclasses import dataclass

from controllers.navigation import (
    Mpu6050NavigationAdapter,
    NavigationController,
    NavigationState,
)
from hardware_io.imu import Mpu6050Imu


Point3 = tuple[float, float, float]
Edge = tuple[int, int]


@dataclass(frozen=True, slots=True)
class WireframeModel:
    """Define vertices and edges for the dashboard's vehicle wireframe."""
    points: tuple[Point3, ...]
    body_edges: tuple[Edge, ...]
    wheel_edges: tuple[Edge, ...]


def _build_jeep_model() -> WireframeModel:
    points: list[Point3] = []
    body_edges: list[Edge] = []
    wheel_edges: list[Edge] = []

    def add_box(
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
        z_min: float,
        z_max: float,
    ) -> None:
        start = len(points)
        points.extend(
            (
                (x_min, y_min, z_min),
                (x_max, y_min, z_min),
                (x_max, y_max, z_min),
                (x_min, y_max, z_min),
                (x_min, y_min, z_max),
                (x_max, y_min, z_max),
                (x_max, y_max, z_max),
                (x_min, y_max, z_max),
            )
        )
        local_edges = (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        )
        body_edges.extend(
            (start + left, start + right)
            for left, right in local_edges
        )

    add_box(-2.15, 2.15, -0.88, 0.88, 0.42, 0.82)
    add_box(0.72, 2.28, -0.82, 0.82, 0.82, 1.08)
    add_box(-1.45, 0.62, -0.78, 0.78, 0.82, 1.72)

    # Sloped windshield and rear pillars give the cabin a Jeep-like profile.
    for y in (-0.78, 0.78):
        start = len(points)
        points.extend(
            (
                (0.62, y, 0.95),
                (0.34, y, 1.72),
                (-1.18, y, 1.72),
                (-1.45, y, 0.88),
            )
        )
        body_edges.extend(
            (
                (start, start + 1),
                (start + 1, start + 2),
                (start + 2, start + 3),
            )
        )

    # Front grille bars and bumpers.
    for y in (-0.6, -0.3, 0.0, 0.3, 0.6):
        start = len(points)
        points.extend(((2.29, y, 0.55), (2.29, y, 0.95)))
        body_edges.append((start, start + 1))
    add_box(2.12, 2.42, -1.0, 1.0, 0.32, 0.45)
    add_box(-2.38, -2.1, -0.98, 0.98, 0.34, 0.47)

    # Four wheels, represented as circles in the X/Z plane.
    wheel_segments = 12
    for wheel_x in (-1.4, 1.42):
        for wheel_y in (-0.98, 0.98):
            start = len(points)
            for segment in range(wheel_segments):
                angle = 2.0 * math.pi * segment / wheel_segments
                points.append(
                    (
                        wheel_x + 0.46 * math.cos(angle),
                        wheel_y,
                        0.43 + 0.46 * math.sin(angle),
                    )
                )
            wheel_edges.extend(
                (
                    start + segment,
                    start + (segment + 1) % wheel_segments,
                )
                for segment in range(wheel_segments)
            )

    return WireframeModel(
        points=tuple(points),
        body_edges=tuple(body_edges),
        wheel_edges=tuple(wheel_edges),
    )


def _rotate_point(
    point: Point3,
    heading_deg: float,
    pitch_deg: float,
    roll_deg: float,
) -> Point3:
    """Rotate a body-frame point by roll, pitch, then heading."""

    x, y, z = point
    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    heading = math.radians(heading_deg)

    # Positive vehicle roll lowers the right side (positive Y).
    y, z = (
        y * math.cos(roll) + z * math.sin(roll),
        -y * math.sin(roll) + z * math.cos(roll),
    )
    # Positive vehicle pitch raises the front (positive X).
    x, z = (
        x * math.cos(pitch) - z * math.sin(pitch),
        x * math.sin(pitch) + z * math.cos(pitch),
    )
    x, y = (
        x * math.cos(heading) - y * math.sin(heading),
        x * math.sin(heading) + y * math.cos(heading),
    )
    return x, y, z


def _project_point(
    point: Point3,
    width: int,
    height: int,
    scale: float,
) -> tuple[float, float]:
    """Project a world point using a fixed isometric camera."""

    x, y, z = point
    camera_heading = math.radians(-35.0)
    view_x = x * math.cos(camera_heading) - y * math.sin(camera_heading)
    view_depth = x * math.sin(camera_heading) + y * math.cos(camera_heading)
    view_y = z - 0.42 * view_depth

    return (
        width / 2.0 + view_x * scale,
        height / 2.0 - view_y * scale + 35.0,
    )


class NavigationVisualizerApp:
    """Display live orientation using a rotating wireframe Jeep."""

    def __init__(
        self,
        controller: NavigationController,
        update_ms: int,
        calibrate_on_start: bool,
        calibration_samples: int,
        calibration_interval_s: float,
    ) -> None:
        self._controller = controller
        self._update_ms = update_ms
        self._calibrate_on_start = calibrate_on_start
        self._calibration_samples = calibration_samples
        self._calibration_interval_s = calibration_interval_s
        self._model = _build_jeep_model()
        self._closed = False

        self._root = tk.Tk()
        self._root.title("OpenRoadCode Navigation Visualizer")
        self._root.geometry("960x640")
        self._root.minsize(640, 420)
        self._root.configure(bg="#071018")

        self._canvas = tk.Canvas(
            self._root,
            bg="#071018",
            highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        controls = tk.Frame(self._root, bg="#0c1924")
        controls.pack(fill=tk.X)
        tk.Button(
            controls,
            text="Calibrate",
            command=self._calibrate,
        ).pack(side=tk.LEFT, padx=8, pady=7)
        tk.Button(
            controls,
            text="Reset Heading",
            command=self._reset_heading,
        ).pack(side=tk.LEFT, padx=4, pady=7)

        self._orientation_text = tk.StringVar(
            value="Heading --   Pitch --   Roll --"
        )
        tk.Label(
            controls,
            textvariable=self._orientation_text,
            fg="#d9f5ff",
            bg="#0c1924",
            font=("TkFixedFont", 11, "bold"),
        ).pack(side=tk.LEFT, padx=18)

        self._status_text = tk.StringVar(value="Starting...")
        tk.Label(
            controls,
            textvariable=self._status_text,
            fg="#79d9ff",
            bg="#0c1924",
        ).pack(side=tk.RIGHT, padx=12)

        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._root.bind("<Escape>", lambda _event: self._close())
        self._root.bind("q", lambda _event: self._close())
        self._root.bind("h", lambda _event: self._reset_heading())
        self._root.bind("c", lambda _event: self._calibrate())

    def run(self) -> None:
        try:
            self._controller.start()
        except Exception as exc:
            self._status_text.set(f"Connection error: {exc}")
        else:
            self._status_text.set("Live navigation data")
            if self._calibrate_on_start:
                self._root.after(150, self._calibrate)
            self._root.after(0, self._poll)

        self._root.mainloop()

    def _poll(self) -> None:
        if self._closed or not self._controller.is_started:
            return

        try:
            state = self._controller.read_state()
            self._draw_state(state)
            calibration = (
                "calibrated"
                if self._controller.calibration is not None
                else "uncalibrated"
            )
            self._status_text.set(f"Live navigation data · {calibration}")
        except Exception as exc:
            self._status_text.set(f"Navigation error: {exc}")
            return

        self._root.after(self._update_ms, self._poll)

    def _draw_state(self, state: NavigationState) -> None:
        self._orientation_text.set(
            f"Heading {state.heading_deg:7.2f}°   "
            f"Pitch {state.pitch_deg:7.2f}°   "
            f"Roll {state.roll_deg:7.2f}°"
        )

        self._canvas.delete("all")
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        scale = min(width / 7.5, height / 5.0)

        rotated = tuple(
            _rotate_point(
                point,
                state.heading_deg,
                state.pitch_deg,
                state.roll_deg,
            )
            for point in self._model.points
        )
        projected = tuple(
            _project_point(point, width, height, scale)
            for point in rotated
        )

        self._draw_reference(width, height)
        self._draw_edges(
            projected,
            self._model.body_edges,
            color="#67d8ff",
            width=2,
        )
        self._draw_edges(
            projected,
            self._model.wheel_edges,
            color="#ffb347",
            width=3,
        )

        linear = state.linear_acceleration_mps2
        self._canvas.create_text(
            18,
            18,
            anchor=tk.NW,
            fill="#9db7c7",
            font=("TkFixedFont", 10),
            text=(
                "X forward · Y right · Z up\n"
                f"Linear acceleration  "
                f"X {linear.x:+.2f}  "
                f"Y {linear.y:+.2f}  "
                f"Z {linear.z:+.2f} m/s²"
            ),
        )

    def _draw_edges(
        self,
        projected: tuple[tuple[float, float], ...],
        edges: tuple[Edge, ...],
        color: str,
        width: int,
    ) -> None:
        for left, right in edges:
            self._canvas.create_line(
                *projected[left],
                *projected[right],
                fill=color,
                width=width,
                capstyle=tk.ROUND,
            )

    def _draw_reference(self, width: int, height: int) -> None:
        center_x = width / 2.0
        center_y = height / 2.0 + 35.0
        radius = min(width, height) * 0.34
        self._canvas.create_oval(
            center_x - radius,
            center_y - radius * 0.42,
            center_x + radius,
            center_y + radius * 0.42,
            outline="#183747",
            width=1,
        )
        self._canvas.create_text(
            center_x,
            center_y - radius * 0.48,
            text="N",
            fill="#3e7087",
            font=("TkDefaultFont", 11, "bold"),
        )

    def _calibrate(self) -> None:
        if not self._controller.is_started:
            self._status_text.set("Navigation sensor is not connected")
            return

        self._status_text.set("Calibrating · keep the vehicle still...")
        self._root.update_idletasks()
        try:
            result = self._controller.calibrate_stationary(
                sample_count=self._calibration_samples,
                sample_interval_s=self._calibration_interval_s,
            )
        except Exception as exc:
            self._status_text.set(f"Calibration error: {exc}")
        else:
            self._status_text.set(
                f"Calibrated from {result.sample_count} samples"
            )

    def _reset_heading(self) -> None:
        if self._controller.is_started:
            self._controller.reset_heading()
            self._status_text.set("Relative heading reset")

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._controller.stop()
        self._root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display a wireframe Jeep using live navigation state."
    )
    parser.add_argument(
        "--address",
        type=lambda value: int(value, 0),
        default=Mpu6050Imu.DEFAULT_ADDRESS,
        help="MPU-6050 I2C address. Default: 0x68",
    )
    parser.add_argument(
        "--update-ms",
        type=int,
        default=50,
        help="Milliseconds between display updates. Default: 50",
    )
    parser.add_argument(
        "--filter-time-constant",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Run stationary calibration after connecting",
    )
    parser.add_argument("--calibration-samples", type=int, default=100)
    parser.add_argument("--calibration-interval", type=float, default=0.01)
    args = parser.parse_args()

    if args.update_ms <= 0:
        parser.error("--update-ms must be greater than zero")
    if args.filter_time_constant < 0:
        parser.error("--filter-time-constant must be zero or greater")
    if args.calibration_samples <= 0:
        parser.error("--calibration-samples must be greater than zero")
    if args.calibration_interval < 0:
        parser.error("--calibration-interval must be zero or greater")
    return args


def main() -> int:
    args = parse_args()
    controller = NavigationController(
        sensor=Mpu6050NavigationAdapter(
            Mpu6050Imu(address=args.address)
        ),
        filter_time_constant_s=args.filter_time_constant,
    )
    app = NavigationVisualizerApp(
        controller=controller,
        update_ms=args.update_ms,
        calibrate_on_start=args.calibrate,
        calibration_samples=args.calibration_samples,
        calibration_interval_s=args.calibration_interval,
    )
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
