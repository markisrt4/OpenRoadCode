from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Callable
from pathlib import Path


SPLASH_IMAGE_PATH = (
    Path(__file__).resolve().parent
    / "assets"
    / "openroadcode-splash.png"
)
SPLASH_BACKGROUND = "#0b0d10"


def show_startup_splash() -> None:
    """Show the optional CarUI startup splash and wait for it to finish."""

    if not _env_bool("CARUI_SPLASH", True):
        return

    splash = StartupSplash(
        image_path=SPLASH_IMAGE_PATH,
        fade_ms=_env_int("CARUI_SPLASH_FADE_MS", 700),
        hold_ms=_env_int("CARUI_SPLASH_HOLD_MS", 1500),
        fullscreen=_env_bool(
            "CARUI_SPLASH_FULLSCREEN",
            _env_bool("CARUI_FULLSCREEN", False),
        ),
        geometry=os.getenv("CARUI_GEOMETRY", "1024x600"),
    )
    splash.show()


class StartupSplash:
    """Tk splash window with a fade-in, hold, and fade-out sequence."""

    def __init__(
        self,
        *,
        image_path: Path,
        fade_ms: int,
        hold_ms: int,
        fullscreen: bool,
        geometry: str,
    ) -> None:
        self._root = tk.Tk(className="OpenRoadCodeSplash")
        self._fade_ms = max(0, fade_ms)
        self._hold_ms = max(0, hold_ms)
        self._image: tk.PhotoImage | None = None

        self._root.title("OpenRoadCode")
        self._root.configure(bg=SPLASH_BACKGROUND)
        self._root.overrideredirect(True)

        if fullscreen:
            self._root.attributes("-fullscreen", True)
        else:
            self._center_window(geometry)

        self._build(image_path)

    def show(self) -> None:
        self._set_opacity(0.0)
        self._root.update_idletasks()
        self._animate_opacity(
            start=0.0,
            end=1.0,
            duration_ms=self._fade_ms,
            on_complete=self._hold,
        )
        self._root.mainloop()

    def _build(self, image_path: Path) -> None:
        try:
            self._image = tk.PhotoImage(file=image_path)
        except tk.TclError as exc:
            print(f"[UI] Unable to load splash logo: {exc}")

        content = tk.Frame(self._root, bg=SPLASH_BACKGROUND)
        content.pack(fill="both", expand=True)

        if self._image is not None:
            tk.Label(
                content,
                image=self._image,
                bg=SPLASH_BACKGROUND,
                bd=0,
            ).place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(
            content,
            text="OPEN ROAD CODE",
            font=("DejaVu Sans", 28, "bold"),
            bg=SPLASH_BACKGROUND,
            fg="#f4f7f9",
        ).place(relx=0.5, rely=0.82, anchor="center")

        tk.Label(
            content,
            text="OPEN SOURCE SOFTWARE FOR THE ROAD",
            font=("DejaVu Sans", 11),
            bg=SPLASH_BACKGROUND,
            fg="#aeb8c0",
        ).place(relx=0.5, rely=0.89, anchor="center")

    def _hold(self) -> None:
        self._root.after(self._hold_ms, self._fade_out)

    def _fade_out(self) -> None:
        self._animate_opacity(
            start=1.0,
            end=0.0,
            duration_ms=self._fade_ms,
            on_complete=self._root.destroy,
        )

    def _animate_opacity(
        self,
        *,
        start: float,
        end: float,
        duration_ms: int,
        on_complete: Callable[[], None],
    ) -> None:
        if duration_ms <= 0:
            self._set_opacity(end)
            on_complete()
            return

        frame_ms = 16
        steps = max(1, duration_ms // frame_ms)

        def render(step: int) -> None:
            ratio = min(1.0, step / steps)
            eased = ratio * ratio * (3.0 - 2.0 * ratio)
            opacity = start + ((end - start) * eased)
            self._set_opacity(opacity)

            if step >= steps:
                on_complete()
                return

            self._root.after(frame_ms, render, step + 1)

        render(0)

    def _set_opacity(self, value: float) -> None:
        try:
            self._root.attributes("-alpha", value)
        except tk.TclError:
            pass

    def _center_window(self, geometry: str) -> None:
        try:
            size = geometry.split("+", 1)[0]
            width_text, height_text = size.lower().split("x", 1)
            width = int(width_text)
            height = int(height_text)
        except (TypeError, ValueError):
            width, height = 1024, 600

        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self._root.geometry(f"{width}x{height}+{x}+{y}")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default
