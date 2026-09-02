#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Fake SDR++ telemetry plugin server for ORC development."""

from __future__ import annotations

import argparse
import math
import socketserver
import time


class TelemetryState:
    def snapshot(self) -> dict[str, str]:
        # Slowly vary the signal values so UIs can prove they are refreshing.
        phase = time.monotonic() / 3.0
        noise = -88.0 + math.sin(phase) * 2.0
        signal = -57.0 + math.sin(phase * 1.7) * 5.0
        return {
            "snr": f"{signal - noise:.3f}",
            "signal_peak": f"{signal:.3f}",
            "noise_floor": f"{noise:.3f}",
            "center_frequency": "104300000.000",
            "bandwidth": "2400000.000",
            "view_bandwidth": "2400000.000",
            "fft_min": "-120.000",
            "fft_max": "0.000",
            "waterfall_min": "-120.000",
            "waterfall_max": "0.000",
            "selected_vfo": "Radio",
        }


STATE = TelemetryState()


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        for raw_line in self.rfile:
            command = raw_line.decode("utf-8", errors="replace").strip()
            if not command:
                continue
            response = self.dispatch(command)
            self.wfile.write((response + "\n").encode("utf-8"))
            self.wfile.flush()

    @staticmethod
    def dispatch(command: str) -> str:
        if command == "PING":
            return "OK"

        values = STATE.snapshot()
        if command == "GET telemetry":
            order = (
                "snr", "signal_peak", "noise_floor", "center_frequency",
                "bandwidth", "view_bandwidth", "fft_min", "fft_max",
                "waterfall_min", "waterfall_max", "selected_vfo",
            )
            fields = " ".join(f"{name}={values[name]}" for name in order)
            return f"TELEMETRY {fields}"

        if command.startswith("GET "):
            name = command[4:].strip()
            if name in values:
                return f"VALUE {name} {values[name]}"

        return "ERROR unknown-command"


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=4534, type=int)
    args = parser.parse_args()

    with Server((args.host, args.port), Handler) as server:
        print(f"Fake SDR++ telemetry server listening on {args.host}:{args.port}")
        print("Signal values vary slowly so polling clients have something to watch.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
