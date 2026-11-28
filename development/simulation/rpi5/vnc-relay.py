"""Relay SSH standard streams to the isolated VNC TCP server."""

import os
import socket
import threading


def main() -> None:
    """Transfer binary RFB traffic in both directions."""
    with socket.create_connection(("127.0.0.1", 5900), timeout=10) as sock:
        sock.settimeout(None)

        def upload() -> None:
            try:
                while data := os.read(0, 65536):
                    sock.sendall(data)
            except OSError:
                pass
            finally:
                try:
                    sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass

        threading.Thread(target=upload, daemon=True).start()
        while data := sock.recv(65536):
            view = memoryview(data)
            while view:
                view = view[os.write(1, view) :]


if __name__ == "__main__":
    main()
