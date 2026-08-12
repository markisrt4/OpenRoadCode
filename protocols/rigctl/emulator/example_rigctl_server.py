#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Stateful example rigctl TCP server for development and component testing."""

from __future__ import annotations

import argparse
import logging
import socketserver
import threading
from dataclasses import dataclass, field

LOG = logging.getLogger("example_rigctl_server")


@dataclass
class RigState:
    frequency_hz: int = 100_000_000
    mode: str = "FM"
    bandwidth_hz: int = 200_000
    running: bool = False
    signal_strength_db: float = -73.0
    snr_db: float = 18.5
    rds_text: str = "OpenRoadCode Example Station"
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)


class RigctlRequestHandler(socketserver.StreamRequestHandler):
    """Handle one or more newline-delimited commands on a TCP connection."""

    def handle(self) -> None:
        while raw_line := self.rfile.readline():
            command = raw_line.decode("utf-8", errors="replace").strip()
            if not command:
                continue

            LOG.info("%s:%s -> %s", *self.client_address, command)
            response = self.server.execute(command)  # type: ignore[attr-defined]
            if response is not None:
                self.wfile.write((response + "\n").encode("utf-8"))
                self.wfile.flush()


class ExampleRigctlServer(socketserver.ThreadingTCPServer):
    """Tiny subset of rigctl plus the SDR++ start/stop extensions."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], state: RigState | None = None):
        super().__init__(address, RigctlRequestHandler)
        self.state = state or RigState()

    def execute(self, command: str) -> str:
        parts = command.split()
        verb = parts[0]

        try:
            with self.state.lock:
                if verb == "F" and len(parts) == 2:
                    frequency_hz = int(parts[1])
                    if frequency_hz <= 0:
                        return "RPRT -1"
                    self.state.frequency_hz = frequency_hz
                    return "RPRT 0"

                if verb == "f" and len(parts) == 1:
                    return str(self.state.frequency_hz)

                if verb == "M" and len(parts) == 3:
                    bandwidth_hz = int(parts[2])
                    if bandwidth_hz < 0:
                        return "RPRT -1"
                    self.state.mode = parts[1].upper()
                    self.state.bandwidth_hz = bandwidth_hz
                    return "RPRT 0"

                if verb == "m" and len(parts) == 1:
                    return f"{self.state.mode}\n{self.state.bandwidth_hz}"

                if command == r"\start":
                    self.state.running = True
                    return "RPRT 0"

                if command == r"\stop":
                    self.state.running = False
                    return "RPRT 0"

                if verb == "l" and len(parts) == 2:
                    level = parts[1].upper()
                    if level == "STRENGTH":
                        return str(self.state.signal_strength_db)
                    if level == "SNR":
                        return str(self.state.snr_db)
                    if level == "RDS":
                        return self.state.rds_text
                    return "RPRT -4"

        except ValueError:
            return "RPRT -1"

        return "RPRT -4"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4532)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    with ExampleRigctlServer((args.host, args.port)) as server:
        host, port = server.server_address
        print(f"Example rigctl server listening on {host}:{port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping example rigctl server")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
