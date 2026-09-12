# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Integrated OpenRoadCode automotive application shell."""
from __future__ import annotations
import signal
import tkinter as tk
from collections.abc import Callable
from datetime import datetime
from .context_rail import ContextRail
from apps.orcUi.core_runtime import MapRuntimeIf
from .home_map_panel import HomeMapPanel
from .navigation_panel import NavigationPanel
from apps.orcUi.navigation_presenter import AttitudePresentationState, PositionPresentationState
from .offroad_panel import OffRoadPanel
from apps.orcUi.orc_theme import ThemeMode, toggle, toggle_label
from .power_dialog import PowerDialog
from .settings_panel import SettingsPanel
from apps.orcUi.theme_runtime import theme_bundle
from apps.orcUi.trip_presenter import TripPresentationState
from .vehicle_panel import VehiclePanel
from apps.orcUi.vehicle_presenter import VehiclePresentationState
from controllers.automotive import (
    AutomotiveTelemetryProfile,
    EngineAnalysis,
    EngineOperatingMode,
    FuelControlMode,
    VehicleConfiguration,
)
from ui.navigation import MapRequestHandlerIf
from ui.screen_ui_if import ScreenUiIf
from ui.system import (
    SystemLifecycleRequestHandlerIf,
    VolumeRequestHandlerIf,
    VolumeUiIf,
)

class OrcUiApp(VolumeUiIf):
    """Own the integrated Tk shell and presentation state."""
    def __init__(
        self,
        *,
        map_runtime: MapRuntimeIf,
        map_request_handler: MapRequestHandlerIf,
        lifecycle_handler: SystemLifecycleRequestHandlerIf,
        telemetry_profile_request: Callable[[AutomotiveTelemetryProfile], None] | None = None,
        vehicle_configuration: VehicleConfiguration = VehicleConfiguration(),
        save_vehicle_configuration: Callable[[VehicleConfiguration], None] | None = None,
    ) -> None:
        self._map_runtime = map_runtime
        self._map_request_handler = map_request_handler
        self._lifecycle_handler = lifecycle_handler
        self._telemetry_profile_request = telemetry_profile_request
        self._vehicle_configuration = vehicle_configuration
        self._save_vehicle_configuration = save_vehicle_configuration
        self._vehicle_configuration_observer: Callable[[VehicleConfiguration], None] | None = None
        self._engine_analysis = EngineAnalysis(
            operating_mode=EngineOperatingMode.UNKNOWN,
            fuel_control_mode=FuelControlMode.UNKNOWN,
            engine_running=None,
            warmed_up=None,
            enrichment_active=None,
            high_load=None,
            forced_induction_active=None,
            fuel_trim_total=None,
            mixture_tracking_error=None,
            throttle_tracking_error=None,
        )
        self._theme_mode = ThemeMode.DARK
        self._theme = theme_bundle(self._theme_mode)
        ui = self._theme.ui
        self._root = tk.Tk()
        self._root.title("OpenRoadCode")
        self._root.geometry("1024x600")
        self._root.minsize(1024, 600)
        self._root.configure(bg=ui.background)
        self._theme_button: tk.Button
        self._power_button: tk.Button
        self._active_nav = "HOME"
        self._nav_items = ["HOME", "NAVIGATION", "RADIO", "VEHICLE", "LIGHTING", "CONTROLS", "SETTINGS"]
        self._nav_buttons: dict[str, tk.Button] = {}
        self._screen_registry: dict[str, ScreenUiIf] = {}
        self._active_screen: ScreenUiIf | None = None
        self._screen_back_action: Callable[[], None] | None = None
        self._screen_status = ""
        self._home_radio_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._home_media_factory: Callable[[tk.Misc], tk.Widget] | None = None
        self._nav_frame: tk.Frame
        self._clock_label: tk.Label
        self._clock_after_id: str | None = None
        self._content: tk.Frame
        self._context_rail: ContextRail | None = None
        self._home_map_panel: HomeMapPanel | None = None
        self._navigation_panel: NavigationPanel | None = None
        self._vehicle_panel: VehiclePanel | None = None
        self._offroad_panel: OffRoadPanel | None = None
        self._settings_panel: SettingsPanel | None = None
        self._vehicle_state = VehiclePresentationState()
        self._trip_state = TripPresentationState()
        self._position_state = PositionPresentationState()
        self._attitude_state = AttitudePresentationState()
        self._volume_percent: float | None = None
        self._volume_muted: bool | None = None
        self._volume_request_handler: VolumeRequestHandlerIf | None = None
        self._volume_label: tk.Label
        self._closing = False
        self._running = False
        self._power_dialog = PowerDialog(
            self._root,
            theme=lambda: self._theme,
            on_exit=self._on_close,
            on_restart=self._restart_ui,
            on_shutdown=self._shutdown_system,
        )
        self._map_runtime.set_theme(self._theme_mode)
        self._build_shell()
        self._update_clock()
    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode
    @property
    def screen_parent(self) -> tk.Misc:
        return self._content
    def set_home_radio_factory(self, factory: Callable[[tk.Misc], tk.Widget] | None) -> None:
        """Install a radio-owned Home summary without coupling the shell to radio."""
        self._home_radio_factory = factory
        if self._running and self._active_nav == "HOME":
            self._show_home()
    def set_home_media_factory(self, factory: Callable[[tk.Misc], tk.Widget] | None) -> None:
        """Install a media-owned Home summary without coupling the shell to Spotify."""
        self._home_media_factory = factory
        if self._running and self._active_nav == "HOME":
            self._show_home()
    def set_vehicle_configuration_observer(
        self,
        observer: Callable[[VehicleConfiguration], None] | None,
    ) -> None:
        self._vehicle_configuration_observer = observer

    def set_volume_request_handler(
        self,
        handler: VolumeRequestHandlerIf | None,
    ) -> None:
        """Connect the shell volume controls to a semantic request handler."""
        self._volume_request_handler = handler
    def set_volume(self, volume_percent: float | None) -> None:
        """Display normalized system volume state in the shell."""
        self._volume_percent = (
            None
            if volume_percent is None
            else max(0.0, min(100.0, volume_percent))
        )
        self._paint_volume()
    def set_muted(self, muted: bool | None) -> None:
        """Display system mute state in the shell."""
        self._volume_muted = muted
        self._paint_volume()
    def register_screen(self, label: str, screen: ScreenUiIf, *, before: str | None = "CONTROLS") -> None:
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
    def navigate_to(self, name: str) -> None:
        """Show a registered screen or built-in shell destination."""
        nav_name = name.strip().upper()
        if not nav_name:
            raise ValueError("Navigation destination must not be empty")
        self._active_nav = nav_name
        self._paint_nav()
        screen = self._screen_registry.get(nav_name)
        if screen is not None:
            screen.show()
            return
        self._deactivate_active_screen()
        handler = {
            "HOME": self._show_home,
            "NAVIGATION": self._show_navigation_panel,
            "VEHICLE": self._show_vehicle_panel,
            "SETTINGS": self._show_settings_panel,
        }.get(nav_name)
        self._show_placeholder(nav_name) if handler is None else handler()
    def activate_screen(self, screen: ScreenUiIf) -> None:
        previous = self._active_screen
        if previous is screen:
            return
        if previous is not None:
            previous.hide()
        self._active_screen = screen
    def clear_screen_content(self) -> None:
        self._clear_content()
    def set_screen_title(self, title: str) -> None:
        title = title.strip()
        self._root.title("OpenRoadCode" if not title else f"OpenRoadCode | {title}")
    def set_screen_back_action(self, action: Callable[[], None]) -> None:
        self._screen_back_action = action
    def set_screen_status(self, message: str) -> None:
        self._screen_status = message
    def schedule_ui_callback(self, delay_ms: int, callback: Callable[[], None]) -> object:
        return self._root.after(delay_ms, callback)
    def cancel_ui_callback(self, callback_id: object) -> None:
        self._root.after_cancel(callback_id)
    def apply_vehicle_state(self, state: VehiclePresentationState) -> None:
        """Apply already-presented vehicle state to mounted shell widgets."""
        if self._closing:
            return
        self._vehicle_state = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.update_vehicle_state(state)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.update_state(state)
    def apply_engine_analysis(self, analysis: EngineAnalysis) -> None:
        if self._closing:
            return
        self._engine_analysis = analysis
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.update_engine_analysis(analysis)

    def apply_trip_state(self, state: TripPresentationState) -> None:
        """Apply already-presented trip state to mounted shell widgets."""
        if self._closing:
            return
        self._trip_state = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.update_trip_state(state)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.update_trip_state(state)
    def apply_position_state(self, state: PositionPresentationState) -> None:
        """Apply already-presented position state to mounted shell widgets."""
        if self._closing:
            return
        self._position_state = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.update_position_state(state)
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.update_position(state)
    def apply_attitude_state(self, state: AttitudePresentationState) -> None:
        """Apply already-presented attitude state to mounted shell widgets."""
        if self._closing:
            return
        self._attitude_state = state
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.update_attitude_state(state)
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.update_attitude(state)
    def run(self) -> None:
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        old_signal_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, self._on_sigint)
        self._running = True
        self._show_home()
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
        self._running = False
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        self._map_runtime.stop()
        try:
            self._root.destroy()
        except tk.TclError:
            pass
    def _build_shell(self) -> None:
        ui = self._theme.ui
        self._root.grid_rowconfigure(1, weight=1)
        self._root.grid_columnconfigure(1, weight=1)
        self._build_top_bar()
        self._build_side_nav()
        self._content = tk.Frame(self._root, bg=ui.background)
        self._content.grid(row=1, column=1, sticky="nsew", padx=(6, 8), pady=6)
        self._build_bottom_bar()
        self._build_footer()
    def _build_top_bar(self) -> None:
        ui = self._theme.ui
        bar = tk.Frame(self._root, bg=ui.surface_alt, height=50)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        bar.grid_columnconfigure(1, weight=1)
        brand = tk.Frame(bar, bg=ui.surface_alt)
        brand.grid(row=0, column=0, sticky="w", padx=(10, 8))
        self._build_logo_mark(brand)
        for letter, color in (("O", ui.accent_primary), ("R", ui.accent_danger), ("C", ui.accent_success)):
            tk.Label(brand, text=letter, fg=color, bg=ui.surface_alt, font=("Sans", 21, "bold"), padx=0, pady=0, bd=0).pack(side=tk.LEFT)
        tk.Label(brand, text="ui", fg=ui.text_muted, bg=ui.surface_alt, font=("Monospace", 12), padx=0).pack(side=tk.LEFT, padx=(3, 0), pady=(5, 0))
        self._clock_label = tk.Label(bar, fg=ui.text, bg=ui.surface_alt, font=("Sans", 17, "bold"))
        self._clock_label.grid(row=0, column=1)
        status = tk.Frame(bar, bg=ui.surface_alt)
        status.grid(row=0, column=2, padx=(8, 14), sticky="e")
        tk.Label(status, text="☁  --°F", fg=ui.text, bg=ui.surface_alt, font=("Sans", 11, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(status, text="GPS  ▮▮▮   WiFi   BT   🚗", fg=ui.text_muted, bg=ui.surface_alt, font=("Sans", 11)).pack(side=tk.LEFT, padx=(0, 10))
        self._power_button = tk.Button(status, text="⏻", command=self._power_dialog.show, bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, bd=0, font=("Sans", 16, "bold"), padx=10, pady=2)
        self._power_button.pack(side=tk.LEFT)
    def _build_logo_mark(self, parent: tk.Misc) -> None:
        ui = self._theme.ui
        logo = tk.Canvas(parent, width=32, height=30, bg=ui.surface_alt, highlightthickness=0, bd=0)
        logo.pack(side=tk.LEFT, padx=(0, 4))
        logo.create_line(16, 3, 3, 26, fill=ui.accent_primary, width=4)
        logo.create_line(3, 26, 29, 26, fill=ui.accent_danger, width=4)
        logo.create_line(29, 26, 16, 3, fill=ui.accent_success, width=4)
        logo.create_line(16, 9, 16, 21, fill=ui.text_muted, width=2, dash=(3, 3))
    def _build_side_nav(self) -> None:
        self._nav_frame = tk.Frame(self._root, bg=self._theme.ui.background, width=112)
        self._nav_frame.grid(row=1, column=0, sticky="ns", padx=(8, 0), pady=6)
        self._nav_frame.grid_propagate(False)
        self._rebuild_side_nav()
    def _rebuild_side_nav(self) -> None:
        if not hasattr(self, "_nav_frame"):
            return
        ui = self._theme.ui
        self._nav_frame.configure(bg=ui.background)
        for child in self._nav_frame.winfo_children():
            child.destroy()
        self._nav_buttons.clear()
        for item in self._nav_items:
            button = tk.Button(self._nav_frame, text=item, command=lambda name=item: self.navigate_to(name), bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, bd=0, font=("Sans", 9), height=3)
            button.pack(fill=tk.X, padx=4, pady=2)
            self._nav_buttons[item] = button
        self._paint_nav()
    def _build_bottom_bar(self) -> None:
        ui = self._theme.ui
        bar = tk.Frame(self._root, bg=ui.background, height=55)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 5))
        bar.grid_propagate(False)
        bar.grid_columnconfigure(0, weight=2)
        for column in range(1, 6):
            bar.grid_columnconfigure(column, weight=1)
        volume = tk.Frame(bar, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        volume.grid(row=0, column=0, sticky="nsew", padx=3)
        volume.grid_columnconfigure(1, weight=1)
        tk.Button(volume, text="−", command=self._request_volume_down, bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, bd=0, font=("Sans", 16, "bold")).grid(row=0, column=0, sticky="ns", padx=4)
        self._volume_label = tk.Label(volume, text=self._volume_text(), bg=ui.surface, fg=ui.text, font=("Sans", 10, "bold"))
        self._volume_label.grid(row=0, column=1)
        tk.Button(volume, text="+", command=self._request_volume_up, bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, bd=0, font=("Sans", 15, "bold")).grid(row=0, column=2, sticky="ns", padx=4)
        for column, text in enumerate(("🎙  Push to Talk", "▣  Front Cam", "▣  SCREEN\nAuto", "☀  BRIGHTNESS\n70%"), start=1):
            tk.Button(bar, text=text, bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, highlightthickness=1, highlightbackground=ui.border, font=("Sans", 9)).grid(row=0, column=column, sticky="nsew", padx=3)
        self._theme_button = tk.Button(bar, text=toggle_label(self._theme_mode), command=self._toggle_theme, bg=ui.control_background, fg=ui.control_text, activebackground=ui.control_active, activeforeground="#ffffff", relief=tk.FLAT, highlightthickness=1, highlightbackground=ui.border, font=("Sans", 9, "bold"))
        self._theme_button.grid(row=0, column=5, sticky="nsew", padx=3)
    def _build_footer(self) -> None:
        ui = self._theme.ui
        footer = tk.Frame(self._root, bg=ui.surface_alt, height=25)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(1, weight=1)
        tk.Label(footer, text="OpenRoadCode", fg=ui.text_muted, bg=ui.surface_alt, font=("Sans", 8)).grid(row=0, column=0, padx=10)
        tk.Label(footer, text="Services: --   |   ZMQ: --", fg=ui.text_muted, bg=ui.surface_alt, font=("Sans", 8)).grid(row=0, column=1)
        tk.Label(footer, text="orcUi prototype", fg=ui.text_muted, bg=ui.surface_alt, font=("Sans", 8)).grid(row=0, column=2, padx=10)
    def _rebuild_shell_theme(self) -> None:
        for child in self._root.winfo_children():
            if child is self._content:
                continue
            child.destroy()
        self._nav_buttons.clear()
        self._root.configure(bg=self._theme.ui.background)
        self._content.configure(bg=self._theme.ui.background)
        self._build_top_bar()
        self._build_side_nav()
        self._build_bottom_bar()
        self._build_footer()
        self._paint_clock()
    def _request_volume_up(self) -> None:
        handler = self._volume_request_handler
        if handler is not None:
            handler.request_volume_up()
    def _request_volume_down(self) -> None:
        handler = self._volume_request_handler
        if handler is not None:
            handler.request_volume_down()
    def _volume_text(self) -> str:
        icon = "🔇" if self._volume_muted else "🔊"
        if self._volume_percent is None:
            return f"{icon} --"
        return f"{icon} {round(self._volume_percent)}%"
    def _paint_volume(self) -> None:
        if hasattr(self, "_volume_label") and self._volume_label.winfo_exists():
            self._volume_label.configure(text=self._volume_text())
    def _restart_ui(self) -> None:
        self._lifecycle_handler.request_restart_ui()
        self._shutdown()
    def _shutdown_system(self) -> None:
        self._lifecycle_handler.request_poweroff()
        self._shutdown()
    def _toggle_theme(self) -> None:
        self._theme_mode = toggle(self._theme_mode)
        self._theme = theme_bundle(self._theme_mode)
        self._map_runtime.set_theme(self._theme_mode)
        self._power_dialog.close()
        self._rebuild_shell_theme()
        if self._active_nav == "HOME":
            self._show_home()
        else:
            self._apply_theme_to_content()
        active_screen = self._active_screen
        set_theme_mode = getattr(active_screen, "set_theme_mode", None)
        if callable(set_theme_mode):
            set_theme_mode(self._theme_mode)
        if self._active_nav != "HOME":
            self._reload_active_map()
    def _apply_theme_to_content(self) -> None:
        bundle = self._theme
        if self._home_map_panel is not None and self._home_map_panel.winfo_exists():
            self._home_map_panel.set_theme_bundle(bundle)
        if self._context_rail is not None and self._context_rail.winfo_exists():
            self._context_rail.set_theme_bundle(bundle)
        if self._navigation_panel is not None and self._navigation_panel.winfo_exists():
            self._navigation_panel.set_theme_bundle(bundle)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.set_theme_bundle(bundle)
        if self._offroad_panel is not None and self._offroad_panel.winfo_exists():
            self._offroad_panel.set_theme(bundle.ui)
    def _reload_active_map(self) -> None:
        if self._home_map_panel is not None and self._home_map_panel.winfo_exists():
            parent_window_id = self._home_map_panel.map_host_window_id
        elif self._navigation_panel is not None and self._navigation_panel.winfo_exists():
            parent_window_id = self._navigation_panel.map_host_window_id
        else:
            return
        self._map_runtime.stop()
        self._root.after(100, lambda: self._start_map_renderer(parent_window_id))
    def _deactivate_active_screen(self) -> None:
        active_screen = self._active_screen
        self._active_screen = None
        if active_screen is not None:
            active_screen.hide()
        self._screen_back_action = None
        self._screen_status = ""
        self._root.title("OpenRoadCode")
    def _paint_nav(self) -> None:
        ui = self._theme.ui
        self._nav_frame.configure(bg=ui.background)
        for name, button in self._nav_buttons.items():
            selected = name == self._active_nav
            button.configure(fg="#ffffff" if selected else ui.control_text, bg=ui.control_active if selected else ui.control_background, activebackground=ui.control_active, activeforeground="#ffffff", highlightbackground=ui.border)
    def _clear_content(self) -> None:
        self._map_runtime.stop()
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.release_telemetry_profile()
        self._context_rail = None
        self._home_map_panel = None
        self._navigation_panel = None
        self._vehicle_panel = None
        self._offroad_panel = None
        self._settings_panel = None
        for child in self._content.winfo_children():
            child.destroy()
    def _show_home(self) -> None:
        self._clear_content()
        self._active_nav = "HOME"
        self._paint_nav()
        ui = self._theme.ui
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_columnconfigure(1, weight=0, minsize=ContextRail.WIDTH)
        self._content.grid_rowconfigure(0, weight=3)
        self._content.grid_rowconfigure(1, weight=2)
        self._home_map_panel = HomeMapPanel(self._content, map_request_handler=self._map_request_handler, theme=self._theme)
        self._home_map_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        self._context_rail = ContextRail(self._content, on_expand=self._show_context_full_panel, theme=self._theme)
        self._context_rail.update_vehicle_state(self._vehicle_state)
        self._context_rail.update_trip_state(self._trip_state)
        self._context_rail.update_position_state(self._position_state)
        self._context_rail.update_attitude_state(self._attitude_state)
        self._context_rail.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(5, 0))
        lower = tk.Frame(self._content, bg=ui.background)
        lower.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(5, 0))
        lower.grid_columnconfigure(0, weight=4)
        lower.grid_columnconfigure(1, weight=1)
        lower.grid_rowconfigure(0, weight=1)
        radio = self._panel(lower, "RADIO", ui.accent_warning)
        radio.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        if self._home_radio_factory is None:
            self._summary(radio, "No radio active", "Choose RF or streaming")
        else:
            self._home_radio_factory(radio).pack(fill=tk.BOTH, expand=True)
        media = self._panel(lower, "MEDIA", ui.accent_primary)
        media.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        if self._home_media_factory is None:
            self._summary(media, "No media", "Playback service")
        else:
            self._home_media_factory(media).pack(fill=tk.BOTH, expand=True)
        self._root.update_idletasks()
        self._start_map_renderer(self._home_map_panel.map_host_window_id)
    def _show_navigation_panel(self) -> None:
        self._clear_content()
        self._active_nav = "NAVIGATION"
        self._paint_nav()
        self._navigation_panel = NavigationPanel(self._content, map_request_handler=self._map_request_handler, on_back=self._show_home, theme_bundle=self._theme)
        self._navigation_panel.pack(fill=tk.BOTH, expand=True)
        self._root.update_idletasks()
        self._start_map_renderer(self._navigation_panel.map_host_window_id)
    def _start_map_renderer(self, parent_window_id: int) -> None:
        try:
            self._map_runtime.launch(parent_window_id)
        except (OSError, RuntimeError) as error:
            print(f"WARNING: map renderer: {type(error).__name__}: {error}")
    def _show_vehicle_panel(self) -> None:
        self._clear_content()
        self._active_nav = "VEHICLE"
        self._paint_nav()
        self._vehicle_panel = VehiclePanel(
            self._content,
            on_back=self._show_home,
            on_telemetry_profile=self._telemetry_profile_request,
            state=self._vehicle_state,
            trip_state=self._trip_state,
            theme_bundle=self._theme,
            vehicle_configuration=self._vehicle_configuration,
            engine_analysis=self._engine_analysis,
        )
        self._vehicle_panel.pack(fill=tk.BOTH, expand=True)
    def _show_settings_panel(self) -> None:
        self._clear_content()
        self._active_nav = "SETTINGS"
        self._paint_nav()
        self._settings_panel = SettingsPanel(
            self._content,
            vehicle_configuration=self._vehicle_configuration,
            on_vehicle_configuration_changed=self._apply_vehicle_configuration,
            on_back=self._show_home,
            theme_bundle=self._theme,
        )
        self._settings_panel.pack(fill=tk.BOTH, expand=True)

    def _apply_vehicle_configuration(
        self,
        configuration: VehicleConfiguration,
    ) -> None:
        self._vehicle_configuration = configuration
        if self._save_vehicle_configuration is not None:
            self._save_vehicle_configuration(configuration)
        if self._vehicle_configuration_observer is not None:
            self._vehicle_configuration_observer(configuration)
        if self._vehicle_panel is not None and self._vehicle_panel.winfo_exists():
            self._vehicle_panel.set_vehicle_configuration(configuration)

    def _show_offroad_panel(self) -> None:
        self._clear_content()
        self._offroad_panel = OffRoadPanel(self._content, on_back=self._show_home, position=self._position_state, attitude=self._attitude_state, theme=self._theme.ui)
        self._offroad_panel.pack(fill=tk.BOTH, expand=True)
    def _on_close(self) -> None:
        self._shutdown()
    def _show_context_full_panel(self, name: str) -> None:
        if name == "VEHICLE" or name == "TRIP":
            self._show_vehicle_panel()
            if name == "TRIP" and self._vehicle_panel is not None:
                self._vehicle_panel.show_trip_view()
        elif name == "OFF-ROAD":
            self._show_offroad_panel()
        else:
            self._show_placeholder(name)
    def _show_placeholder(self, name: str) -> None:
        self._clear_content()
        ui = self._theme.ui
        panel = self._panel(self._content, name, ui.accent_success)
        panel.pack(fill=tk.BOTH, expand=True)
        tk.Label(panel, text=f"{name}\nCOMING NEXT", fg=ui.text, bg=ui.surface, font=("Sans", 24, "bold")).place(relx=0.5, rely=0.5, anchor="center")
    def _panel(self, parent: tk.Misc, title: str, accent: str) -> tk.Frame:
        ui = self._theme.ui
        frame = tk.Frame(parent, bg=ui.surface, highlightthickness=1, highlightbackground=ui.border)
        tk.Label(frame, text=title, fg=accent, bg=ui.surface, font=("Sans", 10, "bold")).pack(anchor="nw", padx=14, pady=(11, 4))
        return frame
    def _summary(self, parent: tk.Misc, primary: str, secondary: str) -> None:
        ui = self._theme.ui
        tk.Label(parent, text=primary, fg=ui.text, bg=ui.surface, font=("Sans", 14, "bold")).pack(anchor="w", padx=16, pady=(12, 2))
        tk.Label(parent, text=secondary, fg=ui.text_muted, bg=ui.surface, font=("Sans", 9)).pack(anchor="w", padx=16)
    def _paint_clock(self) -> None:
        if self._closing:
            return
        text = datetime.now().strftime("%I:%M %p     %a, %b %d").lstrip("0")
        self._clock_label.configure(text=text)
    def _update_clock(self) -> None:
        if self._closing:
            return
        self._clock_after_id = None
        self._paint_clock()
        self._clock_after_id = self._root.after(1000, self._update_clock)
