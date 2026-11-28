# SPDX-License-Identifier: MIT
"""Lightweight ORC splash window for the Linux and Pi launcher."""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from ui.system.startup_splash_ui_if import StartupSplashUiIf
from ui.ui_widget import UiWidget

_ARTWORK = Path(__file__).resolve().parents[3] / "apps/carUi/assets/openroadcode-splash.png"
_BACKGROUND = "#0b1119"
_TEXT = "#eef3f7"


class OrcStartupSplash(UiWidget):
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        root.title("OpenRoadCode")
        root.configure(bg=_BACKGROUND)
        width = min(root.winfo_screenwidth(), 560)
        height = min(root.winfo_screenheight(), 320)
        x = (root.winfo_screenwidth() - width) // 2
        y = (root.winfo_screenheight() - height) // 2
        root.geometry(f"{width}x{height}+{x}+{y}")
        root.overrideredirect(True)
        root.attributes("-topmost", True)

        content = tk.Frame(root, bg=_BACKGROUND)
        content.place(relx=0.5, rely=0.5, anchor="center")
        try:
            self._logo = tk.PhotoImage(file=_ARTWORK).subsample(3, 3)
            heading = tk.Label(content, image=self._logo, bg=_BACKGROUND, bd=0)
        except tk.TclError:
            heading = tk.Label(
                content, text="OpenRoadCode", bg=_BACKGROUND, fg=_TEXT, font=("Sans", 26, "bold")
            )
        heading.pack()
        self._status = tk.Label(
            content,
            text="Getting your dashboard ready",
            bg=_BACKGROUND,
            fg=_TEXT,
            font=("Sans", 15),
        )
        self._status.pack(pady=(6, 18))
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(
            "OrcSplash.Horizontal.TProgressbar", background="#65b9ef", troughcolor="#263545"
        )
        self._progress = ttk.Progressbar(
            content,
            mode="indeterminate",
            length=min(width - 40, 260),
            style="OrcSplash.Horizontal.TProgressbar",
        )
        self._progress.pack()
        self._progress.start(20)
        self._controls = tk.Frame(content, bg=_BACKGROUND)
        self._controls.pack()

    def show_failure(self, detail: str) -> None:
        self._status.configure(text="OpenRoadCode couldn’t start")
        self._progress.stop()
        self._progress.pack_forget()
        ttk.Button(
            self._controls,
            text="Show details",
            command=lambda: messagebox.showerror("OpenRoadCode startup", detail, parent=self._root),
        ).pack(side="left", padx=4)
        ttk.Button(self._controls, text="Close", command=self.close).pack(side="left", padx=4)
        self._root.after(30_000, self.close)

    def close(self) -> None:
        self._root.destroy()


def main() -> None:
    try:
        root = tk.Tk(className="OpenRoadCodeSplash")
        splash: StartupSplashUiIf = OrcStartupSplash(root)
    except tk.TclError as error:
        print(f"Could not show the ORC splash: {error}", file=sys.stderr)
        return

    def handoff(stream, _mask) -> None:
        root.deletefilehandler(stream)
        detail = stream.readline().strip()
        if detail:
            splash.show_failure(detail)
        else:
            splash.close()

    root.createfilehandler(sys.stdin, tk.READABLE, handoff)
    root.mainloop()


if __name__ == "__main__":
    main()
