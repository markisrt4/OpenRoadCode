# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Forward raw PCM from a shared FIFO to Android's AudioTrack bridge."""

from __future__ import annotations

import argparse
import socket
import time
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8771
DEFAULT_CHUNK_BYTES = 4096
DEFAULT_RECONNECT_SECONDS = 0.5


def forward_pcm(
    fifo_path: str | Path,
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    chunk_bytes: int = DEFAULT_CHUNK_BYTES,
    reconnect_seconds: float = DEFAULT_RECONNECT_SECONDS,
) -> None:
    """Continuously forward PCM, reconnecting when the Android sink restarts."""
    fifo = Path(fifo_path)
    while True:
        try:
            with socket.create_connection((host, port), timeout=3.0) as connection:
                connection.settimeout(None)
                with fifo.open("rb", buffering=0) as pcm:
                    while chunk := pcm.read(chunk_bytes):
                        connection.sendall(chunk)
        except (ConnectionError, OSError):
            time.sleep(reconnect_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fifo", type=Path)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--chunk-bytes", type=int, default=DEFAULT_CHUNK_BYTES)
    args = parser.parse_args()
    forward_pcm(args.fifo, host=args.host, port=args.port, chunk_bytes=args.chunk_bytes)


if __name__ == "__main__":
    main()
