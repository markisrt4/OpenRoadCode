# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Integrated OpenRoadCode automotive application shell."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tkinter as tk
from collections.abc import Callable
from datetime import datetime

from apps.launchers.map_renderer_launcher import MapRendererLauncher
from apps.launchers.sdrpp_launcher import sync_sdrpp_theme
from apps.orcUi.context_rail import ContextRail
from apps.orcUi.home_map_panel import HomeMapPanel
from apps.orcUi.navigation_panel import NavigationPanel
from apps.orcUi.navigation_presenter import (
    AttitudePresentationState,
    NavigationPresenter,
    PositionPresentationState,
)
from apps.orcUi.offroad_panel import OffRoadPanel
from apps.orcUi.orc_theme import (
    ThemeMode,
    apply_tk_theme,
    install_map_style,
    toggle,
    toggle_label,
)
from apps.orcUi.radio_panel import RadioPanel
from apps.orcUi.theme_runtime import theme_bundle
from apps.orcUi.vehicle_panel import VehiclePanel
from apps.orcUi.vehicle_presenter import VehiclePresenter, VehiclePresentationState
from frontends.x11 import X11WindowEmbedder
from messaging.contracts.automotive import VEHICLE_STATE_TOPIC, decode_vehicle_state
from messaging.contracts.navigation import (
    ATTITUDE_STATE_TOPIC,
    POSITION_STATE_TOPIC,
    decode_attitude_state,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.zeromq import ZeroMqSubscriber
from messaging.zeromq.endpoints import LOCAL_SUBSCRIBER_ENDPOINT
from ui.screen_ui_if import ScreenUiIf

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
    """Own the integrated Tk application and its runtime-facing adapters."""

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
        self._nav_items = [
            "HOME",
            "NAVIGATION",
            "RADIO",
            "VEHICLE",
            "LIGHTING",
            "CONTROLS",
            "SETTINGS",
        ]
        self._nav_buttons: dict[str, tk.Button] = {}
        self._screen_registry: dict[str, ScreenUiIf] = {}
        self._active_screen: ScreenUiIf | None = None
        self._screen_back_action: Callable[[], None] | None = None
        self._screen_status = ""
        self._nav_frame: tk.Frame
        self._clock_label: tk.Label
        self._content: tk.Frame

        self._context_rail = None
        self._home_map_panel = None
        self._navigation_panel = None
        self._radio_panel = None
        self._radio_embedder = X11WindowEmbedder()
        self._vehicle_panel = None
        self._offroad_panel = None

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
        self._dispatcher.register(
            VEHICLE_STATE_TOPIC,
            decode_vehicle_state,
            self._on_vehicle_message,
        )
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._on_position_message,
        )
        self._dispatcher.register(
            ATTITUDE_STATE_TOPIC,
            decode_attitude_state,
            self._on_attitude_message,
        )

        install_map_style(self._theme_mode)
        self._build_shell()
        self._show_home()
        self._update_clock()

    @property
    def theme_mode(self) -> ThemeMode:
        """Return the active ORC UI theme mode."""
        return self._theme_mode

    @property
    def screen_parent(self) -> tk.Misc:
        """Return the Tk container used by registered screens."""
        return self._content

    def register_screen(
        self,
        label: str,
        screen: ScreenUiIf,
        *,
        before: str | None = "CONTROLS",
    ) -> None:
        """Register a composed screen and expose it in the side navigation."""
        nav_label = label.strip().upper()
        if not nav_label:
            raise ValueError("Screen navigation label must not be empty")
        self._screen_registry[nav_label] = screen
        if nav_label not in self._nav_items:
            if before is not None and before in self._nav_items:
                self._nav_items.insert(self._nav_items.index(before), nav_label)
            else:
                self._nav_items.append(nav_label)
        self._rebuild_side_nav()

    def activate_screen(self, screen: ScreenUiIf) -> None:
        """Make a registered screen the active semantic UI target."""
        previous = self._active_screen
        if previous is screen:
            return
        if previous is not None:
            previous.hide()
        self._active_screen = screen

    def clear_screen_content(self) -> None:
        """Clear the central content area before a screen rebuild."""
        self._clear_content()

    def set_screen_title(self, title: str) -> None:
        """Expose the active screen title through the application window."""
        title = title.strip()
        self._root.title("OpenRoadCode" if not title else f"OpenRoadCode | {title}")

    def set_screen_back_action(self, action: Callable[[], None]) -> None:
        """Store the current screen back action for shell-level input routing."""
        self._screen_back_action = action

    def set_screen_status(self, message: str) -> None:
        """Store active-screen status until the shell status surface is migrated."""
        self._screen_status = message

    def schedule_ui_callback(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> object:
        """Schedule work on Tk's event-loop thread."""
        return self._root.after(delay_ms, callback)

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel pending Tk work previously scheduled by a screen."""
        self._root.after_cancel(callback_id)

    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        old_signal_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._on_sigint)
        self._dispatcher.start()
        try:
            self._root.mainloop()
        except KeyboardInterrupt:
            self._shutdown()
        finally:
            signal.signal(signal.SIGINT, old_signal_handler)
            self._shutdown()

    def _on_sigint(self, _signum, _frame) -> None:
        self._root.after_idle(self._shutdown)

    def _shutdown(self) -> None:
        if self._closing:
            return
        self._closing = True
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
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
            tk.Label(
                brand,
                text=letter,
                fg=color,
                bg=TOP_BG,
                font=("Sans", 21, "bold"),
                padx=0,
                pady=0,
                bd=0,
            ).pack(side=tk.LEFT, padx=0)
        tk.Label(
            brand,
            text="ui",
            fg="#c5ccd2",
            bg=TOP_BG,
            font=("Monospace", 12),
            padx=0,
        ).pack(side=tk.LEFT, padx=(3, 0), pady=(5, 0))

        self._clock_label = tk.Label(
            bar,
            fg=TEXT,
            bg=TOP_BG,
            font=("Sans", 17, "bold"),
        )
        self._clock_label.grid(row=0, column=1)

        status = tk.Frame(bar, bg=TOP_BG)
        status.grid(row=0, column=2, padx=(8, 14), sticky="e")
        tk.Label(
            status,
            text="☁  --°F",
            fg=TEXT,
            bg=TOP_BG,
            font=("Sans", 11, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(
            status,
            text="GPS  ▮▮▮   WiFi   BT   🚗",
            fg="#b8c0c6",
            bg=TOP_BG,
            font=("Sans", 11),
        ).pack(side=tk.LEFT, padx=(0, 10))
        self._power_button = tk.Button(
            status,
            text="⏻",
            command=self._show_power_dialog,
            bg="#101820",
            fg=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 16, "bold"),
            padx=10,
            pady=2,
        )
        self._power_button.pack(side=tk.LEFT)

    @staticmethod
    def _build_logo_mark(parent: tk.Misc) -> None:
        logo = tk.Canvas(
            parent,
            width=32,
            height=30,
            bg=TOP_BG,
            highlightthickness=0,
            bd=0,
        )
        logo.pack(side=tk.LEFT, padx=(0, 4))
        logo.create_line(16, 3, 3, 26, fill=BLUE, width=4)
        logo.create_line(3, 26, 29, 26, fill=RED, width=4)
        logo.create_line(29, 26, 16, 3, fill=GREEN, width=4)
        logo.create_line(16, 9, 16, 21, fill="#d7dde2", width=2, dash=(3, 3))

    def _build_side_nav(self) -> None:
        ui = theme_bundle(self._theme_mode).ui
        self._nav_frame = tk.Frame(self._root, bg=ui.background, width=112)
        self._nav_frame.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=6)
        self._nav_frame.grid_propagate(False)
        self._rebuild_side_nav()

    def _rebuild_side_nav(self) -> None:
        if not hasattr(self, "_nav_frame"):
            return
        ui = theme_bundle(self._theme_mode).ui
        self._nav_frame.configure(bg=ui.background)
        for child in self._nav_frame.winfo_children():
            child.destroy()
        self._nav_buttons.clear()
        for item in self._nav_items:
            button = tk.Button(
                self._nav_frame,
                text=item,
                command=lambda name=item: self._select_nav(name),
                bg=ui.control_background,
                fg=ui.control_text,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                font=("Sans", 9),
                height=3,
            )
            button.pack(fill=tk.X, padx=4, pady=2)
            self._nav_buttons[item] = button
        self._paint_nav()

    def _build_bottom_bar(self) -> None:
        bar = tk.Frame(self._root, bg=BG, height=55)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 5))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=2)
        for column in range(1, 6):
            bar.grid_columnconfigure(column, weight=1)

        volume = tk.Frame(
            bar,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        volume.grid(row=0, column=0, sticky="nsew", padx=3)
        volume.grid_columnconfigure(1, weight=1)
        tk.Button(
            volume,
            text="−",
            command=lambda: self._change_volume(-5),
            bg=PANEL,
            fg=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 16, "bold"),
        ).grid(row=0, column=0, sticky="ns", padx=4)
        self._volume_label = tk.Label(
            volume,
            text="🔊 20%",
            bg=PANEL,
            fg=TEXT,
            font=("Sans", 10, "bold"),
        )
        self._volume_label.grid(row=0, column=1)
        tk.Button(
            volume,
            text="+",
            command=lambda: self._change_volume(5),
            bg=PANEL,
            fg=TEXT,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", 15, "bold"),
        ).grid(row=0, column=2, sticky="ns", padx=4)

        bottom_buttons = [
            "🎙  Push to Talk",
            "▣  Front Cam",
            "▣  SCREEN\nAuto",
            "☀  BRIGHTNESS\n70%",
        ]
        for column, text in enumerate(bottom_buttons, start=1):
            tk.Button(
                bar,
                text=text,
                bg=PANEL,
                fg=TEXT,
                relief=tk.FLAT,
                highlightthickness=1,
                highlightbackground=BORDER,
                font=("Sans", 9),
            ).grid(row=0, column=column, sticky="nsew", padx=3)

        self._theme_button = tk.Button(
            bar,
            text=toggle_label(self._theme_mode),
            command=self._toggle_theme,
            bg=PANEL,
            fg=TEXT,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Sans", 9, "bold"),
        )
        self._theme_button.grid(row=0, column=5, sticky="nsew", padx=3)

    def _change_volume(self, delta: int) -> None:
        self._volume = max(0, min(100, self._volume + delta))
        icon = "🔇" if self._volume == 0 else "🔊"
        self._volume_label.configure(text=f"{icon} {self._volume}%")

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

        actions = (
            ("EXIT UI", self._on_close),
            ("RESTART UI", self._restart_ui),
            ("SHUT DOWN SYSTEM", self._show_shutdown_confirmation),
            ("CANCEL", self._close_power_dialog),
        )
        for text, command in actions:
            tk.Button(
                frame,
                text=text,
                command=command,
                bg="#101820",
                fg=TEXT,
                relief=tk.FLAT,
                width=24,
                pady=8,
                font=("Sans", 10, "bold"),
            ).pack(fill=tk.X, pady=3)
        self._center_power_dialog(dialog)

    def _show_shutdown_confirmation(self) -> None:
        self._shutdown_system()

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
        if shutil.which("systemctl"):
            command = ["systemctl", "poweroff"]
        elif shutil.which("loginctl"):
            command = ["loginctl", "poweroff"]
        else:
            return
        self._map_renderer.stop()
        self._dispatcher.close()
        subprocess.Popen(command)
        self._shutdown()

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
        sync_sdrpp_theme("Light" if self._theme_mode is ThemeMode.LIGHT else "Dark")
        apply_tk_theme(self._root, self._theme_mode)
        active_screen = self._active_screen
        set_theme_mode = getattr(active_screen, "set_theme_mode", None)
        if callable(set_theme_mode):
            set_theme_mode(self._theme_mode)
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
        tk.Label(
            footer,
            text="OpenRoadCode",
            fg="#aab2b8",
            bg=TOP_BG,
            font=("Sans", 8),
        ).grid(row=0, column=0, padx=10)
        tk.Label(
            footer,
            text="Services: --   |   ZMQ: --",
            fg=MUTED,
            bg=TOP_BG,
            font=("Sans", 8),
        ).grid(row=0, column=1)
        tk.Label(
            footer,
            text="orcUi prototype",
            fg=MUTED,
            bg=TOP_BG,
            font=("Sans", 8),
        ).grid(row=0, column=2, padx=10)

    def _select_nav(self, name: str) -> None:
        self._active_nav = name
        self._paint_nav()
        screen = self._screen_registry.get(name)
        if screen is not None:
            screen.show()
            return
        self._deactivate_active_screen()
        handler = {
            "HOME": self._show_home,
            "NAVIGATION": self._show_navigation_panel,
            "RADIO": self._show_radio_panel,
            "VEHICLE": self._show_vehicle_panel,
        }.get(name)
        if handler is None:
            self._show_placeholder(name)
        else:
            handler()

    def _deactivate_active_screen(self) -> None:
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        self._screen_back_action = None
        self._screen_status = ""
        self._root.title("OpenRoadCode")

    def _paint_nav(self) -> None:
        ui = theme_bundle(self._theme_mode).ui
        self._nav_frame.configure(bg=ui.background)
        for name, button in self._nav_buttons.items():
            selected = name == self._active_nav
            button.configure(
                fg="#ffffff" if selected else ui.control_text,
                bg=ui.control_active if selected else ui.control_background,
                activebackground=ui.control_active,
                activeforeground="#ffffff",
                highlightbackground=ui.border,
            )

    def _clear_content(self) -> None:
        self._map_renderer.stop()
        if self._radio_panel is not None and self._radio_panel.winfo_exists():
            self._radio_panel.detach_sdrpp(self._root.winfo_id())
        self._context_rail = None
        self._home_map_panel = None
        self._navigation_panel = None
        self._radio_panel = None
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
        self._home_map_panel.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 5),
            pady=(0, 5),
        )
        self._context_rail = ContextRail(
            self._content,
            on_expand=self._show_context_full_panel,
        )
        self._context_rail.update_vehicle_state(self._vehicle_state)
        self._context_rail.update_position_state(self._position_state)
        self._context_rail.grid(
            row=0,
            column=1,
            rowspan=2,
            sticky="nsew",
            padx=(5, 0),
        )

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

        self._root.update_idletasks()
        self._start_map_renderer(self._home_map_panel.map_host_window_id)

    def _show_navigation_panel(self) -> None:
        self._clear_content()
        self._active_nav = "NAVIGATION"
        self._paint_nav()
        self._navigation_panel = NavigationPanel(self._content, on_back=self._show_home)
        self._navigation_panel.pack(fill=tk.BOTH, expand=True)
        self._root.update_idletasks()
        self._start_map_renderer(self._navigation_panel.map_host_window_id)

    def _start_map_renderer(self, parent_window_id: int) -> None:
        try:
            self._map_renderer.launch(
                display=os.environ.get("DISPLAY", ":1"),
                parent_window_id=parent_window_id,
            )
        except (OSError, RuntimeError) as error:
            print(f"WARNING: map renderer: {type(error).__name__}: {error}")

    def _show_radio_panel(self) -> None:
        self._clear_content()
        self._active_nav = "RADIO"
        self._paint_nav()
        self._radio_panel = RadioPanel(self._content, embedder=self._radio_embedder)
        self._radio_panel.pack(fill=tk.BOTH, expand=True)
        self._root.update_idletasks()
        self._root.after(100, self._attach_existing_sdrpp)

    def _attach_existing_sdrpp(self) -> None:
        panel = self._radio_panel
        if panel is None or not panel.winfo_exists():
            return
        try:
            panel.attach_sdrpp()
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"WARNING: SDR++ embed: {type(error).__name__}: {error}")

    def _show_vehicle_panel(self) -> None:
        self._clear_content()
        self._active_nav = "VEHICLE"
        self._paint_nav()
        self._vehicle_panel = VehiclePanel(
            self._content,
            on_back=self._show_home,
            state=self._vehicle_state,
        )
        self._vehicle_panel.pack(fill=tk.BOTH, expand=True)

    def _show_offroad_panel(self) -> None:
        self._clear_content()
        self._offroad_panel = OffRoadPanel(
            self._content,
            on_back=self._show_home,
            position=self._position_state,
            attitude=self._attitude_state,
        )
        self._offroad_panel.pack(fill=tk.BOTH, expand=True)

    def _on_vehicle_message(self, message) -> None:
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

    def _on_position_message(self, message) -> None:
        state = NavigationPresenter.present_position(message.data)
        if not self._closing:
            self._root.after(0, self._apply_position_state, state)

    def _apply_position_state(self, state: PositionPresentationState) -> None:
        self._position_state = state

    def _on_attitude_message(self, message) -> None:
        self._attitude_state = NavigationPresenter.present_attitude(message.data)

    @staticmethod
    def _on_bus_error(topic, error: Exception) -> None:
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
        self._show_placeholder(name)

    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        panel = self._panel(self._content, name, GREEN)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            panel,
            text=f"{name}\nCOMING NEXT",
            fg=TEXT,
            bg=PANEL,
            font=("Sans", 24, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")

    @staticmethod
    def _panel(parent: tk.Misc, title: str, accent: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=PANEL,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        tk.Label(
            frame,
            text=title,
            fg=accent,
            bg=PANEL,
            font=("Sans", 10, "bold"),
        ).pack(anchor="nw", padx=14, pady=(11, 4))
        return frame

    @staticmethod
    def _summary(parent: tk.Misc, primary: str, secondary: str) -> None:
        tk.Label(
            parent,
            text=primary,
            fg=TEXT,
            bg=PANEL,
            font=("Sans", 14, "bold"),
        ).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(
            parent,
            text=secondary,
            fg=MUTED,
            bg=PANEL,
            font=("Sans", 9),
        ).pack(anchor="w", padx=16)

    def _update_clock(self) -> None:
        if self._closing:
            return
        text = datetime.now().strftime("%I:%M %p     %a, %b %d").lstrip("0")
        self._clock_label.configure(text=text)
        self._root.after(1000, self._update_clock)
