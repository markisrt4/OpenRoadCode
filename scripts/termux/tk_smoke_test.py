# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Minimal Tk smoke test for the Termux/X11 development target."""

import tkinter as tk


def main() -> None:
    root = tk.Tk()
    root.title("OpenRoadCode Termux Test")
    root.geometry("600x400")

    label = tk.Label(
        root,
        text="OpenRoadCode\nTermux + X11 + Tk",
        font=("Sans", 24),
    )
    label.pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
