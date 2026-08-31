# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Manual cross-process X11 embedding test for SDR++."""

from __future__ import annotations

import os
import tkinter as tk

from apps.common.x11_window_embedder import X11WindowEmbedder


def main() -> None:
    root = tk.Tk()
    root.title("ORC X11 Embed Test")
    root.geometry("900x520")

    heading = tk.Label(root, text="OpenRoadCode SDR++ Embed Test")
    heading.pack(fill="x")

    host = tk.Frame(root, bg="black")
    host.pack(fill="both", expand=True)

    status = tk.Label(root, text="Waiting for SDR++...")
    status.pack(fill="x")

    root.update_idletasks()
    host_xid = host.winfo_id()
    embedder = X11WindowEmbedder(os.getenv("DISPLAY"))

    def attach() -> None:
        try:
            sdrpp_xid = embedder.find_window(
                title_contains="SDR++",
                timeout_seconds=0.1,
            )
            embedder.embed(sdrpp_xid, host_xid)
            resize(sdrpp_xid)
            status.config(
                text=f"Embedded SDR++ XID 0x{sdrpp_xid:x} into 0x{host_xid:x}"
            )
        except Exception as exc:
            status.config(text=f"Waiting for SDR++: {exc}")
            root.after(250, attach)

    def resize(child_xid: int) -> None:
        embedder.resize(child_xid, host.winfo_width(), host.winfo_height())
        host.bind(
            "<Configure>",
            lambda event: embedder.resize(child_xid, event.width, event.height),
        )

    def close() -> None:
        embedder.close()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, attach)
    root.mainloop()


if __name__ == "__main__":
    main()
