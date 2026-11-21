# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Manual X11 embedding test using a supplied X11 client process ID."""

from __future__ import annotations

import argparse
import tkinter as tk

from frontends.x11 import X11WindowEmbedder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pid", type=int, help="PID of the X11 client X11 process")
    parser.add_argument("--window-name", default="", help="Optional window title filter")
    args = parser.parse_args()

    root = tk.Tk()
    root.title("ORC X11 Embed Test")
    root.geometry("900x520")

    heading = tk.Label(root, text="OpenRoadCode X11 client Embed Test")
    heading.pack(fill="x")

    host = tk.Frame(root, bg="black")
    host.pack(fill="both", expand=True)

    status = tk.Label(root, text=f"Waiting for X11 client PID {args.pid}...")
    status.pack(fill="x")

    root.update_idletasks()
    embedder = X11WindowEmbedder()

    def attach() -> None:
        try:
            window_id = embedder.embed(
                args.pid,
                host.winfo_id(),
                host.winfo_width(),
                host.winfo_height(),
                window_name=args.window_name,
            )
            status.config(
                text=f"Embedded X11 client XID {window_id} from PID {args.pid}"
            )
            host.bind(
                "<Configure>",
                lambda event: embedder.resize(event.width, event.height),
            )
        except Exception as exc:
            status.config(text=f"Embed failed: {exc}")

    def close() -> None:
        embedder.clear()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, attach)
    root.mainloop()


if __name__ == "__main__":
    main()
