from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from os import PathLike
from typing import Generic, TypeVar

from frontends.tk.runtime import apply_fullscreen


T = TypeVar("T")


class StartupState(Enum):
    PENDING = auto()
    STARTING = auto()
    READY = auto()
    DEGRADED = auto()
    FAILED = auto()


@dataclass(frozen=True)
class StartupItem:
    key: str
    label: str


StartupStatusCallback = Callable[
    [str, StartupState, str],
    None,
]


class StartupSplash(Generic[T]):
    """Display startup progress while application dependencies initialize."""

    def __init__(
        self,
        *,
        items: Sequence[StartupItem],
        image_path: str | PathLike[str] | None = None,
        window_title: str = "Starting",
        heading: str = "STARTING",
        subtitle: str = "INITIALIZING",
        footer: str = "",
        background: str = "#0b0d10",
        fade_ms: int = 500,
        completion_hold_ms: int = 350,
        failure_hold_ms: int = 2500,
        fullscreen: bool = False,
        geometry: str = "1024x600",
    ) -> None:
        self._root = tk.Tk(className="OpenRoadCodeSplash")
        self._items = tuple(items)
        self._fade_ms = max(0, fade_ms)
        self._completion_hold_ms = max(0, completion_hold_ms)
        self._failure_hold_ms = max(0, failure_hold_ms)
        self._background = background
        self._heading = heading
        self._subtitle = subtitle
        self._footer_text = footer

        self._image: tk.PhotoImage | None = None
        self._status_labels: dict[str, tk.Label] = {}
        self._detail_labels: dict[str, tk.Label] = {}
        self._messages: queue.Queue[tuple] = queue.Queue()

        self._result: T | None = None
        self._error: BaseException | None = None
        self._finished = False

        self._root.title(window_title)
        self._root.configure(bg=self._background)

        if fullscreen:
            # Fullscreen already removes normal window decoration. Combining
            # it with override-redirect prevents some Pi window managers from
            # mapping the splash at all.
            self._root.overrideredirect(False)
        else:
            self._root.overrideredirect(True)
            self._center_window(geometry)

        self._build(image_path)

        if fullscreen:
            apply_fullscreen(self._root)

    def run(
        self,
        initializer: Callable[[StartupStatusCallback], T],
    ) -> T:
        """Run initializer in a worker thread while the splash remains responsive."""

        self._set_opacity(0.0)
        self._root.update_idletasks()

        self._animate_opacity(
            start=0.0,
            end=1.0,
            duration_ms=self._fade_ms,
            on_complete=lambda: self._start_initializer(initializer),
        )

        self._root.after(40, self._poll_messages)
        self._root.mainloop()

        if self._error is not None:
            raise self._error

        if not self._finished:
            raise RuntimeError("Startup splash closed before initialization completed")

        return self._result  # type: ignore[return-value]

    def _start_initializer(
        self,
        initializer: Callable[[StartupStatusCallback], T],
    ) -> None:
        thread = threading.Thread(
            target=self._run_initializer,
            args=(initializer,),
            name="openroadcode-initializer",
            daemon=True,
        )
        thread.start()

    def _run_initializer(
        self,
        initializer: Callable[[StartupStatusCallback], T],
    ) -> None:
        try:
            result = initializer(self._post_status)
        except BaseException as exc:
            self._messages.put(("error", exc))
            return

        self._messages.put(("complete", result))

    def _post_status(
        self,
        key: str,
        state: StartupState,
        detail: str = "",
    ) -> None:
        self._messages.put(("status", key, state, detail))

    def _poll_messages(self) -> None:
        try:
            while True:
                message = self._messages.get_nowait()
                kind = message[0]

                if kind == "status":
                    _, key, state, detail = message
                    self._apply_status(key, state, detail)
                elif kind == "complete":
                    _, result = message
                    self._result = result
                    self._finished = True
                    self._root.after(
                        self._completion_hold_ms,
                        self._fade_out,
                    )
                elif kind == "error":
                    _, error = message
                    self._error = error
                    self._apply_global_failure(str(error))
                    self._root.after(
                        self._failure_hold_ms,
                        self._fade_out,
                    )
        except queue.Empty:
            pass

        if self._root.winfo_exists() and not self._finished and self._error is None:
            self._root.after(40, self._poll_messages)

    def _build(self, image_path: str | PathLike[str] | None) -> None:
        if image_path is not None:
            try:
                self._image = tk.PhotoImage(file=image_path)
            except tk.TclError as exc:
                print(f"[UI] Unable to load splash logo: {exc}")

        content = tk.Frame(self._root, bg=self._background)
        content.pack(fill="both", expand=True)

        if self._image is not None:
            tk.Label(
                content,
                image=self._image,
                bg=self._background,
                bd=0,
            ).place(relx=0.5, rely=0.27, anchor="center")

        tk.Label(
            content,
            text=self._heading,
            font=("DejaVu Sans", 26, "bold"),
            bg=self._background,
            fg="#f4f7f9",
        ).place(relx=0.5, rely=0.53, anchor="center")

        tk.Label(
            content,
            text=self._subtitle,
            font=("DejaVu Sans", 11),
            bg=self._background,
            fg="#aeb8c0",
        ).place(relx=0.5, rely=0.59, anchor="center")

        checklist = tk.Frame(content, bg=self._background)
        checklist.place(relx=0.5, rely=0.73, anchor="center")

        for row, item in enumerate(self._items):
            status_label = tk.Label(
                checklist,
                text="○",
                width=2,
                anchor="center",
                font=("DejaVu Sans", 14, "bold"),
                bg=self._background,
                fg="#6f7a82",
            )
            status_label.grid(row=row, column=0, padx=(0, 8), pady=3)

            tk.Label(
                checklist,
                text=item.label,
                width=22,
                anchor="w",
                font=("DejaVu Sans", 12, "bold"),
                bg=self._background,
                fg="#f4f7f9",
            ).grid(row=row, column=1, sticky="w", pady=3)

            detail_label = tk.Label(
                checklist,
                text="Pending",
                width=30,
                anchor="w",
                font=("DejaVu Sans", 10),
                bg=self._background,
                fg="#87939c",
            )
            detail_label.grid(row=row, column=2, sticky="w", pady=3)

            self._status_labels[item.key] = status_label
            self._detail_labels[item.key] = detail_label

        self._footer = tk.Label(
            content,
            text=self._footer_text,
            font=("DejaVu Sans", 10),
            bg=self._background,
            fg="#77828a",
        )
        self._footer.place(relx=0.5, rely=0.94, anchor="center")

    def _apply_status(
        self,
        key: str,
        state: StartupState,
        detail: str,
    ) -> None:
        status_label = self._status_labels.get(key)
        detail_label = self._detail_labels.get(key)
        if status_label is None or detail_label is None:
            print(f"[UI] Unknown startup item: {key}")
            return

        symbol, color, default_detail = {
            StartupState.PENDING: ("○", "#6f7a82", "Pending"),
            StartupState.STARTING: ("⟳", "#4db6ff", "Starting"),
            StartupState.READY: ("✓", "#77d353", "Ready"),
            StartupState.DEGRADED: ("!", "#ffb347", "Limited"),
            StartupState.FAILED: ("✕", "#ff5f56", "Failed"),
        }[state]

        status_label.configure(text=symbol, fg=color)
        detail_label.configure(
            text=detail or default_detail,
            fg=color if state in {StartupState.DEGRADED, StartupState.FAILED} else "#aeb8c0",
        )
        self._root.update_idletasks()

    def _apply_global_failure(self, detail: str) -> None:
        self._footer.configure(
            text=f"STARTUP FAILED: {detail}",
            fg="#ff5f56",
        )

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
