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
    """Drain PCM continuously and forward it whenever Android audio is available.

    The FIFO is intentionally kept open for reading even while the Android
    AudioTrack bridge is unavailable.  Audio is disposable in that state:
    dropping PCM is preferable to backpressuring PulseAudio and stalling the
    SDR++ DSP graph.
    """
    fifo = Path(fifo_path)
    connection: socket.socket | None = None
    next_reconnect = 0.0

    with fifo.open("rb", buffering=0) as pcm:
        while True:
            chunk = pcm.read(chunk_bytes)
            if not chunk:
                continue

            if connection is None:
                now = time.monotonic()
                if now >= next_reconnect:
                    try:
                        connection = socket.create_connection((host, port), timeout=3.0)
                        connection.settimeout(None)
                    except (ConnectionError, OSError):
                        connection = None
                        next_reconnect = time.monotonic() + reconnect_seconds

            if connection is None:
                continue

            try:
                connection.sendall(chunk)
            except (ConnectionError, OSError):
                try:
                    connection.close()
                except OSError:
                    pass
                connection = None
                next_reconnect = time.monotonic() + reconnect_seconds


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
