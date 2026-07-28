"""Standalone demo for VehicleGaugeSubpanel without an OBD-II connection."""

from __future__ import annotations

import math
import signal
import tkinter as tk
from datetime import datetime
from types import SimpleNamespace

from vehicle_gauge_subpanel import VehicleGaugeSubpanel


def main() -> None:
    root = tk.Tk()
    root.title("OpenRoadCode Vehicle Gauges")
    root.geometry("1024x600")
    root.configure(background="#000000")

    panel = VehicleGaugeSubpanel(
        root,
        config_path="~/.config/openroadcode/vehicle_gauges.json",
        columns=4,
    )
    panel.pack(fill="both", expand=True)

    start_ms = root.tk.call("clock", "milliseconds")
    running = True
    shutdown_requested = False
    update_after_id: str | None = None
    signal_after_id: str | None = None

    def shutdown() -> None:
        """Stop scheduled work and close Tk through one idempotent path."""
        nonlocal running, update_after_id, signal_after_id
        if not running:
            return
        running = False
        for after_id in (update_after_id, signal_after_id):
            if after_id is not None:
                try:
                    root.after_cancel(after_id)
                except tk.TclError:
                    pass
        update_after_id = None
        signal_after_id = None
        try:
            root.quit()
            root.destroy()
        except tk.TclError:
            pass

    def request_shutdown(
        _signal_number: int | None = None,
        _frame: object | None = None,
    ) -> None:
        # Signal handlers should not call Tcl directly. The short polling
        # callback below performs the actual shutdown on Tk's event loop.
        nonlocal shutdown_requested
        shutdown_requested = True

    def poll_for_shutdown() -> None:
        nonlocal signal_after_id
        if shutdown_requested:
            shutdown()
            return
        signal_after_id = root.after(50, poll_for_shutdown)

    def update() -> None:
        nonlocal update_after_id
        if not running:
            return
        elapsed = (root.tk.call("clock", "milliseconds") - start_ms) / 1000.0
        wave = (math.sin(elapsed * 0.8) + 1.0) / 2.0
        state = SimpleNamespace(
            timestamp=datetime.now(),
            rpm=850 + wave * 5650,
            boost_psi=-8 + wave * 28,
            speed_mph=wave * 95,
            throttle_pct=8 + wave * 82,
            coolant_temp_f=190 + wave * 25,
            intake_temp_f=70 + wave * 45,
            engine_load_pct=12 + wave * 80,
            control_voltage=13.4 + wave * 0.8,
            fuel_level_pct=72 - (elapsed % 180) / 3,
            odometer_miles=128_459 + elapsed / 3600 * 42,
            trip_miles=(elapsed / 3600 * 42) % 999.9,
            fuel_economy_mpg=25.5 + math.sin(elapsed * 0.25) * 3.5,
            estimated_range_miles=286 - (elapsed % 180) * 0.7,
            ambient_temp_f=73 + math.sin(elapsed * 0.08) * 5,
            tire_pressures_psi={
                "front_left": 34 + math.sin(elapsed * 0.11),
                "front_right": 35 + math.sin(elapsed * 0.13),
                "rear_left": 33 + math.sin(elapsed * 0.09),
                "rear_right": 34 + math.sin(elapsed * 0.12),
            },
            gear=("R", "1", "2", "3", "4", "5", "6")[
                int(elapsed / 3) % 7
            ],
            diagnostic_trouble_codes=(
                ("P0302",) if int(elapsed / 12) % 2 else ()
            ),
            mil_on=bool(int(elapsed / 12) % 2),
        )
        panel.update_state(state, connected=True)
        update_after_id = root.after(100, update)

    root.protocol("WM_DELETE_WINDOW", shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    update()
    poll_for_shutdown()
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # Fallback for Python/Tk builds that raise instead of invoking the
        # installed SIGINT handler while Tcl is active.
        shutdown()
    finally:
        if running:
            shutdown()


if __name__ == "__main__":
    main()
