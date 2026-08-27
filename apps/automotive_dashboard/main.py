# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Standalone graphical consumer of public vehicle telemetry."""

from __future__ import annotations

import argparse
import tkinter as tk

from apps.automotive_dashboard.automotive_dashboard_window import (
    AutomotiveDashboardWindow,
)
from messaging.contracts.automotive import (
    VEHICLE_STATE_TOPIC,
    VehicleStateMessage,
    decode_vehicle_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT


class AutomotiveDashboardApp:
    """Render vehicle-state messages delivered by the OpenRoadCode bus."""

    def __init__(self, endpoint: str) -> None:
        self._root = tk.Tk()
        self._root.title("Automotive Dashboard")
        self._root.geometry("800x480")
        self._root.configure(bg="#08111a")

        self._window = AutomotiveDashboardWindow(self._root)
        self._window.pack(fill=tk.BOTH, expand=True)

        self._dispatcher = MessageDispatcher(
            ZeroMqSubscriber(endpoint),
            error_handler=self._on_bus_error,
        )
        self._dispatcher.register(
            VEHICLE_STATE_TOPIC,
            decode_vehicle_state,
            self._on_vehicle_message,
        )

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._dispatcher.start()
        self._root.mainloop()

    def _on_vehicle_message(self, message: VehicleStateMessage) -> None:
        # Dispatcher handlers run on executor threads. Tk widgets belong to the
        # Tk thread, so marshal the update through after().
        self._root.after(0, self._window.update_vehicle_state, message.data)

    def _on_bus_error(self, topic: str, error: Exception) -> None:
        print(f"WARNING: {topic}: {type(error).__name__}: {error}")

    def _on_close(self) -> None:
        self._dispatcher.close()
        self._root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Display OpenRoadCode vehicle-state bus telemetry."
    )
    parser.add_argument(
        "--endpoint",
        default=LOCAL_SUBSCRIBER_ENDPOINT,
        help="ZeroMQ broker subscriber endpoint",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    AutomotiveDashboardApp(args.endpoint).run()


if __name__ == "__main__":
    main()
