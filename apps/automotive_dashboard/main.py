import argparse
import tkinter as tk

from apps.automotive_dashboard.automotive_dashboard_window import (
    AutomotiveDashboardWindow,
)
from controllers.automotive.obd2 import Elm327ObdAdapter, Obd2Manager
from hardware_io.automotive.elm327 import Elm327Device
from protocols.obd2 import Obd2CommandError, Obd2ConnectionError


class AutomotiveDashboardApp:
    def __init__(self, port: str, baud: int, update_ms: int) -> None:
        self._root = tk.Tk()
        self._root.title("Automotive Dashboard")
        self._root.geometry("800x480")
        self._root.configure(bg="#08111a")

        self._window = AutomotiveDashboardWindow(self._root)
        self._window.pack(fill=tk.BOTH, expand=True)

        self._update_ms = update_ms

        device = Elm327Device(port=port, baud=baud)
        self._manager = Obd2Manager(Elm327ObdAdapter(device))
        self._connected = False

    def run(self) -> None:
        try:
            self._manager.connect()
            self._connected = True
        except Obd2ConnectionError as ex:
            print(f"ERROR: {ex}")

        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._schedule_update()
        self._root.mainloop()

    def _schedule_update(self) -> None:
        if self._connected:
            try:
                state = self._manager.read_state()
                self._window.update_vehicle_state(state)
            except Obd2CommandError as ex:
                print(f"WARNING: {ex}")
            except Obd2ConnectionError as ex:
                print(f"ERROR: {ex}")
                self._connected = False

        self._root.after(self._update_ms, self._schedule_update)

    def _on_close(self) -> None:
        if self._connected:
            self._manager.disconnect()

        self._root.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automotive dashboard app.")
    parser.add_argument("--port", default="/dev/rfcomm0")
    parser.add_argument("--baud", type=int, default=38400)
    parser.add_argument("--update-ms", type=int, default=500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = AutomotiveDashboardApp(
        port=args.port,
        baud=args.baud,
        update_ms=args.update_ms,
    )
    app.run()


if __name__ == "__main__":
    main()
