# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small ELM327-compatible TCP simulator for automotive integration testing."""

from __future__ import annotations

import argparse
import socket

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 35000

# Mode 01 values chosen to look like a running, stationary-ish vehicle. Responses
# include CAN headers and data lengths because Elm327Device initializes ATH1.
_PID_DATA = {
    0x00: bytes.fromhex("183B8001"),
    0x04: bytes((0x66,)),                 # 40% engine load
    0x05: bytes((0x7B,)),                 # 83 C coolant
    0x0B: bytes((0x73,)),                 # 115 kPa manifold pressure
    0x0C: bytes((0x1F, 0x40)),            # 2000 rpm
    0x0D: bytes((0x2D,)),                 # 45 km/h
    0x0F: bytes((0x50,)),                 # 40 C intake air
    0x10: bytes((0x04, 0xD2)),            # 12.34 g/s MAF
    0x11: bytes((0x40,)),                 # ~25% throttle
    0x20: bytes.fromhex("00022001"),
    0x2F: bytes((0x99,)),                 # 60% fuel
    0x33: bytes((0x64,)),                 # 100 kPa barometric pressure
    0x40: bytes.fromhex("40800000"),
    0x42: bytes((0x37, 0x14)),            # 14.100 V
    0x49: bytes((0x33,)),                 # 20% accelerator pedal
}


def _can_response(pid: int, data: bytes) -> bytes:
    payload = bytes((0x41, pid)) + data
    frame = f"7E8{len(payload):02X}{payload.hex().upper()}\r>"
    return frame.encode("ascii")


def _response(command: str) -> bytes:
    normalized = "".join(command.upper().split())
    if normalized == "ATZ":
        return b"ELM327 v1.5\r>"
    if normalized == "ATI":
        return b"ELM327 v1.5 OpenRoadCode Simulator\r>"
    if normalized.startswith("AT"):
        return b"OK\r>"
    if len(normalized) == 4 and normalized.startswith("01"):
        try:
            pid = int(normalized[2:], 16)
        except ValueError:
            return b"?\r>"
        data = _PID_DATA.get(pid)
        return b"NO DATA\r>" if data is None else _can_response(pid, data)
    return b"?\r>"


def _serve_client(client: socket.socket, address: tuple[str, int]) -> None:
    print(f"ELM327 simulator client connected: {address[0]}:{address[1]}")
    pending = bytearray()
    while True:
        data = client.recv(4096)
        if not data:
            return
        pending.extend(data)
        while b"\r" in pending:
            raw_command, _, remainder = pending.partition(b"\r")
            pending[:] = remainder
            command = raw_command.decode("ascii", errors="replace").strip()
            if not command:
                continue
            response = _response(command)
            print(f">>> {command}")
            print(f"<<< {response.decode('ascii', errors='replace').strip()}")
            client.sendall(response)


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a simulated ELM327 over TCP.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        print(f"OpenRoadCode ELM327 TCP simulator listening on {args.host}:{args.port}")
        print("Ctrl+C to stop")
        try:
            while True:
                client, address = server.accept()
                with client:
                    try:
                        _serve_client(client, address)
                    except (ConnectionError, OSError) as exc:
                        print(f"ELM327 simulator client disconnected: {exc}")
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
