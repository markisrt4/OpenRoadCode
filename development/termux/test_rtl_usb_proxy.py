#!/usr/bin/env python3
"""Probe the OpenRoadCode Android RTL-SDR USB proxy without claiming the radio."""
from __future__ import annotations

import socket
import struct

HOST = "127.0.0.1"
PORT = 35100
MAGIC = 0x4F524355
VERSION = 1
OP_INFO = 1


def read_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("RTL-SDR USB proxy closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_i32(sock: socket.socket) -> int:
    return struct.unpack(">i", read_exact(sock, 4))[0]


def main() -> None:
    with socket.create_connection((HOST, PORT), timeout=3.0) as sock:
        sock.sendall(struct.pack(">IHH", MAGIC, VERSION, OP_INFO))
        result = read_i32(sock)
        if result != 0:
            length = read_i32(sock)
            message = read_exact(sock, length).decode("utf-8", "replace")
            raise RuntimeError(f"RTL-SDR USB proxy error: {message}")

        vendor_id = read_i32(sock)
        product_id = read_i32(sock)
        interface_count = read_i32(sock)
        print(f"RTL-SDR USB proxy: {HOST}:{PORT}")
        print(f"device: {vendor_id:04x}:{product_id:04x}")
        print(f"interfaces: {interface_count}")

        for _ in range(interface_count):
            interface_id = read_i32(sock)
            interface_class = read_i32(sock)
            interface_subclass = read_i32(sock)
            interface_protocol = read_i32(sock)
            endpoint_count = read_i32(sock)
            print(
                f"  interface {interface_id}: class={interface_class} "
                f"subclass={interface_subclass} protocol={interface_protocol}"
            )
            for _ in range(endpoint_count):
                address = read_i32(sock)
                attributes = read_i32(sock)
                direction = read_i32(sock)
                endpoint_type = read_i32(sock)
                max_packet_size = read_i32(sock)
                print(
                    f"    endpoint 0x{address:02x}: attributes={attributes} "
                    f"direction=0x{direction:02x} type={endpoint_type} "
                    f"max_packet={max_packet_size}"
                )

        if (vendor_id, product_id) != (0x0BDA, 0x2838):
            raise RuntimeError(
                f"Expected RTL2832U 0bda:2838, got {vendor_id:04x}:{product_id:04x}"
            )


if __name__ == "__main__":
    main()
