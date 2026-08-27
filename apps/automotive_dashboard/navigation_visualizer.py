# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk wireframe vehicle visualizer for public navigation telemetry."""

from __future__ import annotations

import argparse
import math
import tkinter as tk
from dataclasses import dataclass

from apps.automotive_dashboard.navigation_bus_state import NavigationBusState
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    IMU_STATE_TOPIC,
    decode_attitude_state,
    decode_imu_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from services.navigation.endpoints import DEFAULT_NAVIGATION_COMMAND_ENDPOINT
from ui.navigation.navigation_request_handler_if import NavigationRequestHandlerIf

Point3 = tuple[float, float, float]
Edge = tuple[int, int]


@dataclass(frozen=True, slots=True)
class WireframeModel:
    """Define vertices and edges for the dashboard vehicle wireframe."""

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
            (start + left, start + right) for left, right in local_edges
        )

    add_box(-2.15, 2.15, -0.88, 0.88, 0.42, 0.82)
    add_box(0.72, 2.28, -0.82, 0.82, 0.82, 1.08)
    add_box(-1.45, 0.62, -0.78, 0.78, 0.82, 1.72)

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

    for y in (-0.6, -0.3, 0.0, 0.3, 0.6):
        start = len(points)
        points.extend(((2.29, y, 0.55), (2.29, y, 0.95)))
        body_edges.append((start, start + 1))

    add_box(2.12, 2.42, -1.0, 1.0, 0.32, 0.45)
    add_box(-2.38, -2.1, -0.98, 0.98, 0.34, 0.47)

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

    y, z = (
        y * math.cos(roll) + z * math.sin(roll),
        -y * math.sin(roll) + z * math.cos(roll),
    )
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
    """Display bus-fed orientation using a rotating wireframe Jeep."""

    def __init__(
        self,
        state: NavigationBusState,
        commands: NavigationRequestHandlerIf,
        update_ms: int,
        calibrate_on_start: bool,
    ) -> None:
        self._state = state
        self._commands = commands
        self._update_ms = update_ms
        self._calibrate_on_start = calibrate_on_start
        self._calibration_requested = False
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
        tk.Button(controls, text="Calibrate", command=self._calibrate).pack(
            side=tk.LEFT, padx=8, pady=7
        )
        tk.Button(controls, text="Reset Heading", command=self._reset_heading).pack(
            side=tk.LEFT, padx=4, pady=7
        )

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

        self._status_text = tk.StringVar(value="Waiting for navigation telemetry")
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
        """Run the Tk event loop; telemetry arrives through the shared cache."""
        self._root.after(0, self._poll)
        self._root.mainloop()

    def _poll(self) -> None:
        if self._closed:
            return

        snapshot = self._state.snapshot()
        self._status_text.set(snapshot.status)
        if snapshot.connected:
            self._draw_snapshot(snapshot)
            if self._calibrate_on_start and not self._calibration_requested:
                self._calibration_requested = True
                self._root.after(0, self._calibrate)

        self._root.after(self._update_ms, self._poll)

    def _draw_snapshot(self, state) -> None:
        heading = state.heading_deg or 0.0
        pitch = state.pitch_deg or 0.0
        roll = state.roll_deg or 0.0
        self._orientation_text.set(
            f"Heading {heading:7.2f}°   Pitch {pitch:7.2f}°   Roll {roll:7.2f}°"
        )

        self._canvas.delete("all")
        width = max(1, self._canvas.winfo_width())
        height = max(1, self._canvas.winfo_height())
        scale = min(width / 7.5, height / 5.0)

        rotated = tuple(
            _rotate_point(point, heading, pitch, roll)
            for point in self._model.points
        )
        projected = tuple(
            _project_point(point, width, height, scale)
            for point in rotated
        )

        self._draw_reference(width, height)
        self._draw_edges(projected, self._model.body_edges, "#67d8ff", 2)
        self._draw_edges(projected, self._model.wheel_edges, "#ffb347", 3)

        linear = state.linear_acceleration_mps2
        if linear is not None:
            self._canvas.create_text(
                18,
                18,
                anchor=tk.NW,
                fill="#9db7c7",
                font=("TkFixedFont", 10),
                text=(
                    "X forward · Y right · Z up\n"
                    f"Linear acceleration  X {linear.x:+.2f}  "
                    f"Y {linear.y:+.2f}  Z {linear.z:+.2f} m/s²"
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
        self._status_text.set("Calibrating · keep the vehicle still...")
        self._root.update_idletasks()
        try:
            self._commands.request_stationary_calibration()
        except Exception as exc:
            self._status_text.set(f"Calibration error: {exc}")
        else:
            self._status_text.set("Stationary calibration complete")

    def _reset_heading(self) -> None:
        try:
            self._commands.request_heading_reset()
        except Exception as exc:
            self._status_text.set(f"Heading reset error: {exc}")
        else:
            self._status_text.set("Relative heading reset")

    def _close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display a wireframe Jeep using navigation bus telemetry."
    )
    parser.add_argument("--endpoint", default=LOCAL_SUBSCRIBER_ENDPOINT)
    parser.add_argument("--command-endpoint", default=DEFAULT_NAVIGATION_COMMAND_ENDPOINT)
    parser.add_argument(
        "--update-ms",
        type=int,
        default=50,
        help="Milliseconds between display updates. Default: 50",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Request stationary calibration after telemetry connects",
    )
    args = parser.parse_args()
    if args.update_ms <= 0:
        parser.error("--update-ms must be greater than zero")
    return args


def _build_dispatcher(endpoint: str, state: NavigationBusState) -> MessageDispatcher:
    from messaging.zeromq.subscriber import ZeroMqSubscriber

    dispatcher = MessageDispatcher(ZeroMqSubscriber(endpoint), error_handler=state.set_error)
    dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, state.set_attitude)
    dispatcher.register(IMU_STATE_TOPIC, decode_imu_state, state.set_imu)
    return dispatcher


def main() -> int:
    from services.navigation.zeromq_navigation_request_handler import (
        ZeroMqNavigationRequestHandler,
    )

    args = parse_args()
    state = NavigationBusState()
    dispatcher = _build_dispatcher(args.endpoint, state)
    commands = ZeroMqNavigationRequestHandler(args.command_endpoint)
    app = NavigationVisualizerApp(
        state=state,
        commands=commands,
        update_ms=args.update_ms,
        calibrate_on_start=args.calibrate,
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
