#!/usr/bin/env python3
"""Standalone fake SDR++ remote-control server for protocol validation."""

from __future__ import annotations

import argparse
import socketserver
from dataclasses import dataclass


@dataclass
class RemoteControlState:
    themes: tuple[str, ...] = ("Dark", "Light", "Dracula", "Grey")
    current_theme: str = "Dark"

    def handle(self, command: str) -> str:
        command = command.strip()
        if not command:
            return "ERROR empty-command"

        if command == "PING":
            return "OK"

        if command == "GET theme":
            return f"VALUE theme {self.current_theme}"

        if command == "GET themes":
            return f"VALUES themes {'|'.join(self.themes)}"

        prefix = "SET theme "
        if command.startswith(prefix):
            requested = command[len(prefix):].strip()
            if requested not in self.themes:
                return "ERROR invalid-value"
            self.current_theme = requested
            return "OK"

        return "ERROR unknown-command"


class RemoteControlRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        state: RemoteControlState = self.server.state  # type: ignore[attr-defined]
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"[connect] {peer}", flush=True)

        while raw_line := self.rfile.readline():
            command = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
            response = state.handle(command)
            print(f"[rx] {command!r}", flush=True)
            print(f"[tx] {response!r}", flush=True)
            self.wfile.write((response + "\n").encode("utf-8"))
            self.wfile.flush()

        print(f"[disconnect] {peer}", flush=True)


class RemoteControlTestServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        state: RemoteControlState,
    ) -> None:
        self.state = state
        super().__init__(server_address, RemoteControlRequestHandler)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fake SDR++ remote-control server for validating line protocol exchanges."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=4533)
    parser.add_argument(
        "--themes",
        default="Dark,Light,Dracula,Grey",
        help="Comma-separated themes exposed by GET themes.",
    )
    parser.add_argument(
        "--theme",
        default="Dark",
        help="Initial current theme.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    themes = tuple(value.strip() for value in args.themes.split(",") if value.strip())
    if not themes:
        raise SystemExit("At least one theme is required")
    if args.theme not in themes:
        raise SystemExit(f"Initial theme {args.theme!r} is not in --themes")

    state = RemoteControlState(themes=themes, current_theme=args.theme)
    with RemoteControlTestServer((args.host, args.port), state) as server:
        print(
            f"Fake SDR++ remote-control server listening on {args.host}:{args.port}",
            flush=True,
        )
        print(f"Themes: {', '.join(themes)}", flush=True)
        print(f"Current theme: {state.current_theme}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping.", flush=True)


if __name__ == "__main__":
    main()
