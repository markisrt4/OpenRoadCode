# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Top-level radio chooser and SDR++ launch handoff for orcUi."""

from __future__ import annotations

import os
import threading
import time
import tkinter as tk

from apps.launchers.sdrpp_launcher import SDRPPLauncher, SDRPPProfile
from apps.orcUi.radio_panel import RadioPanel
from config.radio_config_manager import load_radio_config
from controllers.radio.radio_profiles import RadioProfileCatalog
from frontends.x11 import X11WindowEmbedder

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
RED = "#f15a16"


class LaunchAwareRadioPanel(RadioPanel):
    """Radio panel that can present SDR++ startup state inside its X11 host."""

    def __init__(self, parent: tk.Misc, *, embedder: X11WindowEmbedder) -> None:
        super().__init__(parent, embedder=embedder)
        self._launch_status = tk.Label(
            self._host,
            text="Loading SDR++…",
            bg="#000000",
            fg=TEXT,
            font=("Sans", 20, "bold"),
            padx=24,
            pady=18,
        )
        self._launch_status.place(relx=0.5, rely=0.5, anchor="center")

    def show_loading(self, text: str = "Loading SDR++…") -> None:
        self._launch_status.configure(text=text, fg=TEXT)
        self._launch_status.place(relx=0.5, rely=0.5, anchor="center")
        self._launch_status.lift()

    def hide_loading(self) -> None:
        self._launch_status.place_forget()


class RadioEntryPanel(tk.Frame):
    """Offer RF or streaming radio before constructing the active radio UI."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        embedder: X11WindowEmbedder | None = None,
        launcher: SDRPPLauncher | None = None,
    ) -> None:
        super().__init__(parent, bg=BG)
        self._embedder = embedder or X11WindowEmbedder()
        self._display = os.environ.get("DISPLAY", ":1")
        self._launcher = launcher or SDRPPLauncher(
            profile=self._default_sdrpp_profile(),
            fullscreen=False,
            embedded=True,
        )
        self._radio_panel: LaunchAwareRadioPanel | None = None
        self._launching = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._chooser = tk.Frame(self, bg=BG)
        self._chooser.grid(row=0, column=0, sticky="nsew")
        self._chooser.grid_columnconfigure(0, weight=1, uniform="radio-source")
        self._chooser.grid_columnconfigure(1, weight=1, uniform="radio-source")
        self._chooser.grid_rowconfigure(0, weight=1)
        self._build_choice_buttons()
        self._streaming_page = self._build_streaming_page()

    @staticmethod
    def _default_sdrpp_profile() -> SDRPPProfile:
        catalog = RadioProfileCatalog()
        profile = catalog.profile("fm_radio") if any(item.key == "fm_radio" for item in catalog.profiles) else catalog.profiles[0]
        config = load_radio_config(profile.config_path)
        start_frequency_hz = config.radio_range.start_frequency_hz if config.radio_range is not None else None
        return SDRPPProfile(
            name=profile.label,
            mode=config.default_mode.name,
            step_hz=config.default_mode.step_hz,
            start_frequency_hz=start_frequency_hz,
        )

    def _build_choice_buttons(self) -> None:
        rf_card = tk.Frame(self._chooser, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        rf_card.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=18)
        rf_card.grid_columnconfigure(0, weight=1)
        rf_card.grid_rowconfigure(0, weight=1)
        self._rf_button = tk.Button(
            rf_card,
            text="RF RADIO\n\n▶\n\nSDR++ / SDR",
            command=self._launch_rf_radio,
            bg=PANEL,
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=GREEN,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 22, "bold"),
        )
        self._rf_button.grid(row=0, column=0, sticky="nsew")

        streaming_card = tk.Frame(self._chooser, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        streaming_card.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=18)
        streaming_card.grid_columnconfigure(0, weight=1)
        streaming_card.grid_rowconfigure(0, weight=1)
        self._streaming_button = tk.Button(
            streaming_card,
            text="STREAMING RADIO\n\n◉\n\nINTERNET STATIONS",
            command=self._show_streaming_coming_soon,
            bg=PANEL,
            fg=TEXT,
            activebackground="#17232d",
            activeforeground=BLUE,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 22, "bold"),
        )
        self._streaming_button.grid(row=0, column=0, sticky="nsew")

        self._status = tk.Label(
            self._chooser,
            text="Choose a radio source",
            bg=BG,
            fg=MUTED,
            font=("Sans", 10),
        )
        self._status.grid(row=1, column=0, columnspan=2, pady=(0, 10))

    def _build_streaming_page(self) -> tk.Frame:
        page = tk.Frame(self, bg=BG)
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(0, weight=1)
        card = tk.Frame(page, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        card.grid(row=0, column=0, sticky="nsew", padx=12, pady=18)
        tk.Label(card, text="STREAMING RADIO", bg=PANEL, fg=BLUE, font=("Sans", 18, "bold")).place(relx=0.5, rely=0.36, anchor="center")
        tk.Label(card, text="COMING SOON", bg=PANEL, fg=TEXT, font=("Sans", 30, "bold")).place(relx=0.5, rely=0.50, anchor="center")
        tk.Label(card, text="Regional internet stations, cached artwork, favorites, and more.", bg=PANEL, fg=MUTED, font=("Sans", 11)).place(relx=0.5, rely=0.62, anchor="center")
        tk.Button(card, text="‹ BACK TO RADIO", command=self._show_chooser, bg="#101820", fg=TEXT, activebackground="#17232d", activeforeground=BLUE, relief=tk.FLAT, bd=0, font=("Sans", 10, "bold"), padx=16, pady=9).place(relx=0.5, rely=0.76, anchor="center")
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
        self._radio_panel = LaunchAwareRadioPanel(self, embedder=self._embedder)
        self._radio_panel.grid(row=0, column=0, sticky="nsew")
        self._radio_panel.show_loading("Loading SDR++…")
        self.update_idletasks()
        threading.Thread(target=self._launch_rf_worker, name="orcui-sdrpp-launch-watch", daemon=True).start()

    def _launch_rf_worker(self) -> None:
        launch_error: list[Exception] = []

        def launch() -> None:
            try:
                self._launcher.launch(self._display)
            except Exception as error:
                launch_error.append(error)

        launcher_thread = threading.Thread(target=launch, name="orcui-sdrpp-launch", daemon=True)
        launcher_thread.start()

        process_id: int | None = None
        deadline = time.monotonic() + 12.0
        while time.monotonic() < deadline and not launch_error:
            try:
                process_id = self._launcher.window_process_id(timeout_seconds=0.25)
                break
            except RuntimeError:
                if not launcher_thread.is_alive():
                    break
                time.sleep(0.05)

        if process_id is not None:
            self.after(0, lambda pid=process_id: self._attach_rf_radio(pid))
            return

        launcher_thread.join()
        if launch_error:
            self.after(0, lambda exc=launch_error[0]: self._show_launch_error(exc))
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
        self._status.configure(text=f"SDR++: {type(error).__name__}: {error}", fg=RED)
        print(f"WARNING: SDR++ launch/embed: {type(error).__name__}: {error}")

    def detach_sdrpp(self, parent_window_id: int) -> None:
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.detach_sdrpp(parent_window_id)
