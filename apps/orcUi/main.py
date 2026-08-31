# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Entry point for the integrated OpenRoadCode automotive UI."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tkinter as tk
from datetime import datetime

from apps.launchers.map_renderer_launcher import MapRendererLauncher
from apps.orcUi.context_rail import ContextRail
from apps.orcUi.home_map_panel import HomeMapPanel
from apps.orcUi.navigation_panel import NavigationPanel
from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    NavigationPresenter,
    PositionPresentationState,
)
from apps.orcUi.offroad_panel import OffRoadPanel
from apps.orcUi.orc_theme import ThemeMode, apply_tk_theme, install_map_style, toggle, toggle_label
from apps.orcUi.vehicle_panel import VehiclePanel
from apps.orcUi.vehicle_presenter import VehiclePresenter, VehiclePresentationState
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, VehicleStateMessage, decode_vehicle_state
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    AttitudeStateMessage,
    PositionStateMessage,
    decode_attitude_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT

BG = "#05090d"
PANEL = "#0b1117"
BORDER = "#25313b"
TEXT = "#edf2f5"
MUTED = "#89959e"
GREEN = "#84ce1f"
BLUE = "#168bd1"
RED = "#f15a16"
PURPLE = "#a25ce5"
YELLOW = "#d6ad22"
TOP_BG = "#020406"


class OrcUiApp:
    """Top-level ORC cockpit shell."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title("OpenRoadCode")
        self._root.geometry("1024x600")
        self._root.minsize(1024, 600)
        self._root.configure(bg=BG)
        self._theme_mode = ThemeMode.DARK
        self._theme_button: tk.Button
        self._power_button: tk.Button
        self._power_dialog: tk.Toplevel | None = None
        self._active_nav = "HOME"
        self._nav_buttons: dict[str, tk.Button] = {}
        self._clock_label: tk.Label
        self._content: tk.Frame
        self._context_rail: ContextRail | None = None
        self._home_map_panel: HomeMapPanel | None = None
        self._navigation_panel: NavigationPanel | None = None
        self._vehicle_panel: VehiclePanel | None = None
        self._offroad_panel: OffRoadPanel | None = None
        self._map_renderer = MapRendererLauncher()
        self._vehicle_state = VehiclePresentationState()
        self._position_state = PositionPresentationState()
        self._attitude_state = AttitudePresentationState()
        self._volume = 20
        self._volume_label: tk.Label
        self._closing = False
        self._dispatcher = MessageDispatcher(
            ZeroMqSubscriber(LOCAL_SUBSCRIBER_ENDPOINT),
            error_handler=self._on_bus_error,
        )
        self._dispatcher.register(VEHICLE_STATE_TOPIC, decode_vehicle_state, self._on_vehicle_message)
        self._dispatcher.register(POSITION_STATE_TOPIC, decode_position_state, self._on_position_message)
        self._dispatcher.register(ATTITUDE_STATE_TOPIC, decode_attitude_state, self._on_attitude_message)
        install_map_style(self._theme_mode)
        self._build_shell()
        self._show_home()
        self._update_clock()

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        previous_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._on_sigint)
        self._dispatcher.start()
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            self._shutdown()
        finally:
            signal.signal(signal.SIGINT, previous_sigint)
            self._shutdown()

    def _on_sigint(self, _signum: int, _frame) -> None:
        self._root.after_idle(self._shutdown)

    def _shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._map_renderer.stop()
        self._dispatcher.close()
        try:
            self._root.destroy()
        except tk.TclError:
            pass

    def _build_shell(self) -> None:
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(1, weight=1)
        self._build_top_bar()
        self._build_side_nav()
        self._content = tk.Frame(self._root, bg=BG)
        self._content.grid(row=1, column=1, sticky="nsew", padx=(6, 8), pady=6)
        self._build_bottom_bar()
        self._build_footer()

    def _build_top_bar(self) -> None:
        bar = tk.Frame(self._root, bg=TOP_BG, height=50)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        brand = tk.Frame(bar, bg=TOP_BG)
        brand.grid(row=0, column=0, sticky="w", padx=(10, 8))
        self._build_logo_mark(brand)
        for letter, color in (("O", BLUE), ("R", RED), ("C", GREEN)):
            tk.Label(brand, text=letter, fg=color, bg=TOP_BG, font=("Sans", 21, "bold"), padx=0, pady=0, bd=0).pack(side=tk.LEFT, padx=0)
        tk.Label(brand, text="ui", fg="#c5ccd2", bg=TOP_BG, font=("Monospace", 12), padx=0).pack(side=tk.LEFT, padx=(3, 0), pady=(5, 0))
        self._clock_label = tk.Label(bar, fg=TEXT, bg=TOP_BG, font=("Sans", 17, "bold"))
        self._clock_label.grid(row=0, column=1)
        status = tk.Frame(bar, bg=TOP_BG)
        status.grid(row=0, column=2, padx=(8, 14), sticky="e")
        tk.Label(status, text="☁  --°F", fg=TEXT, bg=TOP_BG, font=("Sans", 11, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(status, text="GPS  ▮▮▮   WiFi   BT   🚗", fg="#b8c0c6", bg=TOP_BG, font=("Sans", 11)).pack(side=tk.LEFT, padx=(0, 10))
        self._power_button = tk.Button(
            status,
            text="⏻",
            command=self._show_power_dialog,
            bg="#101820",
            fg=TEXT,
            activebackground="#121b23",
            activeforeground=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 16, "bold"),
            padx=10,
            pady=2,
            cursor="hand2",
        )
        self._power_button.pack(side=tk.LEFT)

    @staticmethod
    def _build_logo_mark(parent: tk.Misc) -> None:
        logo = tk.Canvas(parent, width=32, height=30, bg=TOP_BG, highlightthickness=0, bd=0)
        logo.pack(side=tk.LEFT, padx=(0, 4))
        logo.create_line(16, 3, 3, 26, fill=BLUE, width=4)
        logo.create_line(3, 26, 29, 26, fill=RED, width=4)
        logo.create_line(29, 26, 16, 3, fill=GREEN, width=4)
        logo.create_line(16, 9, 16, 21, fill="#d7dde2", width=2, dash=(3, 3))

    def _build_side_nav(self) -> None:
        nav = tk.Frame(self._root, bg="#070c11", width=112)
        nav.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=6)
        nav.grid_propagate(False)
        for item in ["HOME", "NAVIGATION", "RADIO", "VEHICLE", "LIGHTING", "CONTROLS", "SETTINGS"]:
            button = tk.Button(nav, text=item, command=lambda name=item: self._select_nav(name), bg="#070c11", fg="#c7cdd2", activebackground="#101820", activeforeground=GREEN, relief=tk.FLAT, bd=0, font=("Sans", 9), height=3, cursor="hand2")
            button.pack(fill=tk.X, padx=4, pady=2)
            self._nav_buttons[item] = button
        self._paint_nav()

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self._root, bg=BG, height=55)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 5))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=2)
        for col in range(1, 6):
            bar.grid_columnconfigure(col, weight=1)
        volume = tk.Frame(bar, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        volume.grid(row=0, column=0, sticky="nsew", padx=3)
        volume.grid_columnconfigure(1, weight=1)
        tk.Button(volume, text="−", command=lambda: self._change_volume(-5), bg=PANEL, fg=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 16, "bold")).grid(row=0, column=0, sticky="ns", padx=4)
        self._volume_label = tk.Label(volume, text="🔊 20%", bg=PANEL, fg=TEXT, font=("Sans", 10, "bold"))
        self._volume_label.grid(row=0, column=1)
        tk.Button(volume, text="+", command=lambda: self._change_volume(5), bg=PANEL, fg=TEXT, relief=tk.FLAT, bd=0, font=("Sans", 15, "bold")).grid(row=0, column=2, sticky="ns", padx=4)
        for col, text in enumerate(["🎙  Push to Talk", "▣  Front Cam", "▣  SCREEN\nAuto", "☀  BRIGHTNESS\n70%"], start=1):
            tk.Button(bar, text=text, bg=PANEL, fg=TEXT, relief=tk.FLAT, highlightthickness=1, highlightbackground=BORDER, font=("Sans", 9)).grid(row=0, column=col, sticky="nsew", padx=3)
        self._theme_button = tk.Button(
            bar,
            text=toggle_label(self._theme_mode),
            command=self._toggle_theme,
            bg=PANEL,
            fg=TEXT,
            activebackground="#121b23",
            activeforeground=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Sans", 9, "bold"),
            cursor="hand2",
        )
        self._theme_button.grid(row=0, column=5, sticky="nsew", padx=3)

    def _change_volume(self, delta: int) -> None:
        self._volume = max(0, min(100, self._volume + delta))
        self._volume_label.configure(text=f"{'🔇' if self._volume == 0 else '🔊'} {self._volume}%")

    def _show_power_dialog(self) -> None:
        if self._power_dialog is not None and self._power_dialog.winfo_exists():
            self._power_dialog.lift()
            return

        dialog = tk.Toplevel(self._root)
        self._power_dialog = dialog
        dialog.title("OpenRoadCode Power")
        dialog.transient(self._root)
        dialog.resizable(False, False)
        dialog.configure(bg=PANEL)
        dialog.protocol("WM_DELETE_WINDOW", self._close_power_dialog)

        frame = tk.Frame(dialog, bg=PANEL, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            frame,
            text="POWER",
            fg=TEXT,
            bg=PANEL,
            font=("Sans", 16, "bold"),
        ).pack(pady=(0, 4))
        tk.Label(
            frame,
            text="System actions are intentionally two taps away.",
            fg=MUTED,
            bg=PANEL,
            font=("Sans", 9),
        ).pack(pady=(0, 14))

        for text, command in (
            ("EXIT UI", self._on_close),
            ("RESTART UI", self._restart_ui),
            ("SHUT DOWN SYSTEM", self._show_shutdown_confirmation),
            ("CANCEL", self._close_power_dialog),
        ):
            tk.Button(
                frame,
                text=text,
                command=command,
                bg="#101820",
                fg=TEXT,
                activebackground="#121b23",
                activeforeground=TEXT,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=BORDER,
                width=24,
                pady=8,
                font=("Sans", 10, "bold"),
                cursor="hand2",
            ).pack(fill=tk.X, pady=3)

        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(dialog, self._theme_mode)
        self._center_power_dialog(dialog)

    def _show_shutdown_confirmation(self) -> None:
        dialog = self._power_dialog
        if dialog is None or not dialog.winfo_exists():
            return
        for child in dialog.winfo_children():
            child.destroy()

        frame = tk.Frame(dialog, bg=PANEL, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            frame,
            text="SHUT DOWN SYSTEM?",
            fg=RED,
            bg=PANEL,
            font=("Sans", 15, "bold"),
        ).pack(pady=(2, 7))
        tk.Label(
            frame,
            text="This stops OpenRoadCode and powers off the host.",
            fg=MUTED,
            bg=PANEL,
            font=("Sans", 9),
        ).pack(pady=(0, 14))
        tk.Button(
            frame,
            text="CONFIRM SHUTDOWN",
            command=self._shutdown_system,
            bg="#3a1212",
            fg=TEXT,
            activebackground="#521818",
            activeforeground=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=RED,
            pady=9,
            font=("Sans", 10, "bold"),
            cursor="hand2",
        ).pack(fill=tk.X, pady=3)
        tk.Button(
            frame,
            text="BACK",
            command=self._reopen_power_dialog,
            bg="#101820",
            fg=TEXT,
            activebackground="#121b23",
            activeforeground=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            pady=9,
            font=("Sans", 10, "bold"),
            cursor="hand2",
        ).pack(fill=tk.X, pady=3)
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(dialog, self._theme_mode)
        self._center_power_dialog(dialog)

    def _reopen_power_dialog(self) -> None:
        self._close_power_dialog()
        self._show_power_dialog()

    def _close_power_dialog(self) -> None:
        dialog = self._power_dialog
        self._power_dialog = None
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def _restart_ui(self) -> None:
        self._map_renderer.stop()
        self._dispatcher.close()
        os.execv(sys.executable, [sys.executable, "-m", "apps.orcUi"])

    def _shutdown_system(self) -> None:
        command: list[str] | None = None
        if shutil.which("systemctl"):
            command = ["systemctl", "poweroff"]
        elif shutil.which("loginctl"):
            command = ["loginctl", "poweroff"]

        if command is None:
            self._show_power_error(
                "System shutdown is unavailable on this host.\n"
                "Exit UI is still available."
            )
            return

        self._map_renderer.stop()
        self._dispatcher.close()
        try:
            subprocess.Popen(command)
        except OSError as error:
            self._show_power_error(f"Shutdown failed: {error}")
            return
        self._shutdown()

    def _show_power_error(self, message: str) -> None:
        dialog = self._power_dialog
        if dialog is None or not dialog.winfo_exists():
            return
        for child in dialog.winfo_children():
            child.destroy()
        frame = tk.Frame(dialog, bg=PANEL, padx=18, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="POWER", fg=RED, bg=PANEL, font=("Sans", 15, "bold")).pack(pady=(0, 8))
        tk.Label(frame, text=message, fg=TEXT, bg=PANEL, font=("Sans", 9), justify=tk.CENTER).pack(pady=(0, 12))
        tk.Button(
            frame,
            text="BACK",
            command=self._reopen_power_dialog,
            bg="#101820",
            fg=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            pady=8,
            cursor="hand2",
        ).pack(fill=tk.X)
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(dialog, self._theme_mode)
        self._center_power_dialog(dialog)

    def _center_power_dialog(self, dialog: tk.Toplevel) -> None:
        dialog.update_idletasks()
        width = dialog.winfo_reqwidth()
        height = dialog.winfo_reqheight()
        x = self._root.winfo_rootx() + max(0, (self._root.winfo_width() - width) // 2)
        y = self._root.winfo_rooty() + max(0, (self._root.winfo_height() - height) // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

    def _toggle_theme(self) -> None:
        self._theme_mode = toggle(self._theme_mode)
        install_map_style(self._theme_mode)
        apply_tk_theme(self._root, self._theme_mode)
        self._theme_button.configure(text=toggle_label(self._theme_mode))
        self._paint_nav()
        self._reload_active_map()

    def _reload_active_map(self) -> None:
        if self._home_map_panel is not None and self._home_map_panel.winfo_exists():
            parent_window_id = self._home_map_panel.map_host_window_id
        elif self._navigation_panel is not None and self._navigation_panel.winfo_exists():
            parent_window_id = self._navigation_panel.map_host_window_id
        else:
            return
        self._map_renderer.stop()
        self._root.after(100, lambda: self._start_map_renderer(parent_window_id))

    def _build_footer(self) -> None:
        footer = tk.Frame(self._root, bg=TOP_BG, height=25)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(1, weight=1)
        tk.Label(footer, text="OpenRoadCode", fg="#aab2b8", bg=TOP_BG, font=("Sans", 8)).grid(row=0, column=0, padx=10)
        tk.Label(footer, text="Services: --   |   ZMQ: --", fg=MUTED, bg=TOP_BG, font=("Sans", 8)).grid(row=0, column=1)
        tk.Label(footer, text="orcUi prototype", fg=MUTED, bg=TOP_BG, font=("Sans", 8)).grid(row=0, column=2, padx=10)

    def _select_nav(self, name: str) -> None:
        self._active_nav = name
        self._paint_nav()
        if name == "HOME":
            self._show_home()
        elif name == "NAVIGATION":
            self._show_navigation_panel()
        elif name == "VEHICLE":
            self._show_vehicle_panel()
        else:
            self._show_placeholder(name)

    def _paint_nav(self) -> None:
        light = self._theme_mode is ThemeMode.LIGHT
        inactive_fg = "#3c4a54" if light else "#c7cdd2"
        inactive_bg = "#e4e9ed" if light else "#070c11"
        active_bg = "#d5dde3" if light else "#101820"
        for name, button in self._nav_buttons.items():
            active = name == self._active_nav
            button.configure(fg=GREEN if active else inactive_fg, bg=active_bg if active else inactive_bg)

    def _clear_content(self) -> None:
        self._map_renderer.stop()
        self._context_rail = None
        self._home_map_panel = None
        self._navigation_panel = None
        self._vehicle_panel = None
        self._offroad_panel = None
        for child in self._content.winfo_children():
            child.destroy()

    def _show_home(self) -> None:
        self._clear_content()
        self._active_nav = "HOME"
        self._paint_nav()
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_columnconfigure(1, weight=0, minsize=ContextRail.WIDTH)
        self._content.grid_rowconfigure(0, weight=3)
        self._content.grid_rowconfigure(1, weight=2)
        self._home_map_panel = HomeMapPanel(self._content)
        self._home_map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        self._context_rail = ContextRail(self._content, on_expand=self._show_context_full_panel)
        self._context_rail.update_vehicle_state(self._vehicle_state)
        self._context_rail.update_position_state(self._position_state)
        self._context_rail.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))
        lower = tk.Frame(self._content, bg=BG)
        lower.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
        lower.grid_columnconfigure(0, weight=1)
        lower.grid_columnconfigure(1, weight=1)
        lower.grid_rowconfigure(0, weight=1)
        radio = self._panel(lower, "RADIO", PURPLE)
        radio.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._summary(radio, "101.1 FM", "Radio service")
        media = self._panel(lower, "MEDIA", BLUE)
        media.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self._summary(media, "No media", "Playback service")
        tk.Label(media, text="▂▅▃▇▄▆▂▅", fg=BLUE, bg=PANEL, font=("Sans", 14, "bold")).pack(anchor="w", padx=16, pady=(7, 0))
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(self._content, self._theme_mode)
        self._root.update_idletasks()
        self._start_map_renderer(self._home_map_panel.map_host_window_id)

    def _show_navigation_panel(self) -> None:
        self._clear_content()
        self._active_nav = "NAVIGATION"
        self._paint_nav()
        self._navigation_panel = NavigationPanel(
            self._content,
            on_back=self._show_home,
        )
        self._navigation_panel.pack(fill=tk.BOTH, expand=True)
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(self._navigation_panel, self._theme_mode)
        self._root.update_idletasks()
        self._start_map_renderer(self._navigation_panel.map_host_window_id)

    def _start_map_renderer(self, parent_window_id: int) -> None:
        display = os.environ.get("DISPLAY", ":1")
        try:
            self._map_renderer.launch(
                display=display,
                parent_window_id=parent_window_id,
            )
        except (OSError, RuntimeError) as error:
            print(f"WARNING: map renderer: {type(error).__name__}: {error}")

    def _show_vehicle_panel(self) -> None:
        self._clear_content()
        self._active_nav = "VEHICLE"
        self._paint_nav()
        self._vehicle_panel = VehiclePanel(self._content, on_back=self._show_home, state=self._vehicle_state)
        self._vehicle_panel.pack(fill=tk.BOTH, expand=True)
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(self._vehicle_panel, self._theme_mode)

    def _show_offroad_panel(self) -> None:
        self._clear_content()
        self._offroad_panel = OffRoadPanel(
            self._content,
            on_back=self._show_home,
            position=self._position_state,
            attitude=self._attitude_state,
        )
        self._offroad_panel.pack(fill=tk.BOTH, expand=True)
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(self._offroad_panel, self._theme_mode)

    def _on_vehicle_message(self, message: VehicleStateMessage) -> None:
        state = VehiclePresenter.present(message.data)
        if not self._closing:
            self._root.after(0, self._apply_vehicle_state, state)

    def _apply_vehicle_state(self, state: VehiclePresentationState) -> None:
        if self._closing:
            return
        self._vehicle_state = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.update_vehicle_state(state)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.update_state(state)

    def _on_position_message(self, message: PositionStateMessage) -> None:
        state = NavigationPresenter.present_position(message.data)
        if not self._closing:
            self._root.after(0, self._apply_position_state, state)

    def _apply_position_state(self, state: PositionPresentationState) -> None:
        if self._closing:
            return
        self._position_state = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.update_position_state(state)
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.update_position(state)

    def _on_attitude_message(self, message: AttitudeStateMessage) -> None:
        state = NavigationPresenter.present_attitude(message.data)
        if not self._closing:
            self._root.after(0, self._apply_attitude_state, state)

    def _apply_attitude_state(self, state: AttitudePresentationState) -> None:
        if self._closing:
            return
        self._attitude_state = state
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.update_attitude(state)

    @staticmethod
    def _on_bus_error(topic: str, error: Exception) -> None:
        print(f"WARNING: {topic}: {type(error).__name__}: {error}")

    def _on_close(self) -> None:
        self._shutdown()

    def _show_context_full_panel(self, name: str) -> None:
        if name == "VEHICLE":
            self._show_vehicle_panel()
            return
        if name == "OFF-ROAD":
            self._show_offroad_panel()
            return
        self._clear_content()
        accent = {"TRIP": BLUE}.get(name, GREEN)
        panel = self._panel(self._content, name, accent)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Button(panel, text="‹ HOME", command=self._show_home, bg="#101820", fg=TEXT, relief=tk.FLAT, font=("Sans", 11, "bold"), padx=14, pady=7).pack(anchor="nw", padx=14, pady=10)
        tk.Label(panel, text=f"FULL {name} PANEL", fg=accent, bg=PANEL, font=("Sans", 28, "bold")).place(relx=.5, rely=.44, anchor="center")
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(panel, self._theme_mode)

    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        panel = self._panel(self._content, name, GREEN)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(panel, text=f"{name}\nCOMING NEXT", fg=TEXT, bg=PANEL, font=("Sans", 24, "bold")).place(relx=.5, rely=.5, anchor="center")
        if self._theme_mode is ThemeMode.LIGHT:
            apply_tk_theme(panel, self._theme_mode)

    @staticmethod
    def _panel(parent: tk.Misc, title: str, accent: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        tk.Label(frame, text=title, fg=accent, bg=PANEL, font=("Sans", 10, "bold")).pack(anchor="nw", padx=14, pady=(11, 4))
        return frame

    @staticmethod
    def _summary(parent: tk.Frame, primary: str, secondary: str) -> None:
        tk.Label(parent, text=primary, fg=TEXT, bg=PANEL, font=("Sans", 14, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(parent, text=secondary, fg=MUTED, bg=PANEL, font=("Sans", 9)).pack(anchor="w", padx=16)

    def _update_clock(self) -> None:
        if self._closing:
            return
        now = datetime.now()
        self._clock_label.configure(text=now.strftime("%I:%M %p     %a, %b %d").lstrip("0"))
        self._root.after(1000, self._update_clock)


def main() -> None:
    OrcUiApp().run()


if __name__ == "__main__":
    main()
