# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level radio chooser and SDR++ presentation handoff for orcUi."""

from __future__ import annotations

import threading
import time
import tkinter as tk

from apps.orcUi.radio_application_service import RadioApplicationServiceIf
from apps.orcUi.radio_panel import RadioPanel
from frontends.x11 import X11WindowEmbedder
from ui.theme import ThemeBundle


class LaunchAwareRadioPanel(RadioPanel):
    """Radio panel that can present SDR++ startup state inside its X11 host."""

    def __init__(self, parent: tk.Misc, *, embedder: X11WindowEmbedder, theme: ThemeBundle) -> None:
        super().__init__(parent, embedder=embedder, theme=theme)
        self._launch_status = tk.Label(self._host, text="Loading SDR++…", bg=theme.ui.background, fg=theme.ui.text, font=("Sans", 20, "bold"), padx=24, pady=18)
        self._launch_status.place(relx=0.5, rely=0.5, anchor="center")

    def show_loading(self, text: str = "Loading SDR++…") -> None:
        self._launch_status.configure(text=text, fg=self._theme.ui.text)
        self._launch_status.place(relx=0.5, rely=0.5, anchor="center")
        self._launch_status.lift()

    def hide_loading(self) -> None:
        self._launch_status.place_forget()


class RadioEntryPanel(tk.Frame):
    """Offer RF or streaming radio and host the active radio presentation."""

    def __init__(self, parent: tk.Misc, *, radio_application: RadioApplicationServiceIf, theme: ThemeBundle, embedder: X11WindowEmbedder | None = None) -> None:
        self._theme = theme
        ui = theme.ui
        super().__init__(parent, bg=ui.background)
        self._embedder = embedder or X11WindowEmbedder()
        self._radio_application = radio_application
        self._radio_panel: LaunchAwareRadioPanel | None = None
        self._launching = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._chooser = tk.Frame(self, bg=ui.background)
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._chooser.grid_columnconfigure(0, weight=1, uniform="radio-source")
        self._chooser.grid_columnconfigure(1, weight=1, uniform="radio-source")
        self._chooser.grid_rowconfigure(0, weight=1)
        self._build_choice_buttons()
        self._streaming_page = self._build_streaming_page()

    def _build_choice_buttons(self) -> None:
        ui = self._theme.ui
        rf_card = tk.Frame(self._chooser, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        rf_card.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=18)
        rf_card.grid_columnconfigure(0, weight=1)
        rf_card.grid_rowconfigure(0, weight=1)
        self._rf_button = tk.Button(rf_card, text="RF RADIO\n\n▶\n\nSDR++ / SDR", command=self._launch_rf_radio, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_success, relief=tk.FLAT, bd=0, font=("Sans", 22, "bold"))
        self._rf_button.grid(row=0, column=0, sticky="nsew")

        streaming_card = tk.Frame(self._chooser, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        streaming_card.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=18)
        streaming_card.grid_columnconfigure(0, weight=1)
        streaming_card.grid_rowconfigure(0, weight=1)
        self._streaming_button = tk.Button(streaming_card, text="STREAMING RADIO\n\n◉\n\nINTERNET STATIONS", command=self._show_streaming_coming_soon, bg=ui.surface, fg=ui.text, activebackground=ui.control_background, activeforeground=ui.accent_primary, relief=tk.FLAT, bd=0, font=("Sans", 22, "bold"))
        self._streaming_button.grid(row=0, column=0, sticky="nsew")

        self._status = tk.Label(self._chooser, text="Choose a radio source", bg=ui.background, fg=ui.text_muted, font=("Sans", 10))
        self._status.grid(row=1, column=0, columnspan=2, pady=(0, 10))

    def _build_streaming_page(self) -> tk.Frame:
        ui = self._theme.ui
        page = tk.Frame(self, bg=ui.background)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        card = tk.Frame(page, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        card.grid(row=0, column=0, sticky="nsew", padx=12, pady=18)
        tk.Label(card, text="STREAMING RADIO", bg=ui.surface, fg=ui.accent_primary, font=("Sans", 18, "bold")).place(relx=0.5, rely=0.36, anchor="center")
        tk.Label(card, text="COMING SOON", bg=ui.surface, fg=ui.text, font=("Sans", 30, "bold")).place(relx=0.5, rely=0.50, anchor="center")
        tk.Label(card, text="Regional internet stations, cached artwork, favorites, and more.", bg=ui.surface, fg=ui.text_muted, font=("Sans", 11)).place(relx=0.5, rely=0.62, anchor="center")
        tk.Button(card, text="‹ BACK TO RADIO", command=self._show_chooser, bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=16, pady=9).place(relx=0.5, rely=0.76, anchor="center")
        return page

    def _show_streaming_coming_soon(self) -> None:
        self._chooser.grid_remove()
        self._streaming_page.grid(row=0, column=0, sticky="nsew")

    def _show_chooser(self) -> None:
        self._streaming_page.grid_remove()
        self._chooser.grid(row=0, column=0, sticky="nsew")

    def _launch_rf_radio(self) -> None:
        if self._launching:
            return
        self._launching = True
        self._chooser.grid_remove()
        self._radio_panel = LaunchAwareRadioPanel(self, embedder=self._embedder, theme=self._theme)
        self._radio_panel.grid(row=0, column=0, sticky="nsew")
        self._radio_panel.show_loading("Loading SDR++…")
        self.update_idletasks()
        threading.Thread(target=self._present_rf_worker, name="orcui-sdrpp-present", daemon=True).start()

    def _present_rf_worker(self) -> None:
        presentation_error: list[Exception] = []

        def present() -> None:
            try:
                self._radio_application.present()
            except Exception as error:
                presentation_error.append(error)

        presentation_thread = threading.Thread(target=present, name="orcui-sdrpp-present-request", daemon=True)
        presentation_thread.start()

        process_id: int | None = None
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline and not presentation_error:
            try:
                process_id = self._radio_application.window_process_id(timeout_seconds=0.25)
                break
            except RuntimeError:
                if not presentation_thread.is_alive():
                    break
                time.sleep(0.05)

        if process_id is not None:
            self.after(0, lambda pid=process_id: self._attach_rf_radio(pid))
            return

        presentation_thread.join()
        if presentation_error:
            self.after(0, lambda exc=presentation_error[0]: self._show_launch_error(exc))
            return
        self.after(0, lambda: self._attach_rf_radio(0))

    def _attach_rf_radio(self, process_id: int) -> None:
        panel = self._radio_panel
        if panel is None or not panel.winfo_exists():
            return
        try:
            panel.attach_sdrpp(process_id)
            panel.hide_loading()
        except Exception as error:
            self._show_launch_error(error)
            return
        self._launching = False

    def _show_launch_error(self, error: Exception) -> None:
        if not self.winfo_exists():
            return
        self._launching = False
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.destroy()
        self._radio_panel = None
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._rf_button.configure(state=tk.NORMAL, text="RF RADIO\n\n▶\n\nSDR++ / SDR")
        self._streaming_button.configure(state=tk.NORMAL)
        self._status.configure(text=f"SDR++: {type(error).__name__}: {error}", fg=self._theme.ui.accent_danger)
        print(f"WARNING: SDR++ launch/embed: {type(error).__name__}: {error}")

    def detach_sdrpp(self, parent_window_id: int) -> None:
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.detach_sdrpp(parent_window_id)
