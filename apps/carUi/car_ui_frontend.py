# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Tk frontend entry point for the Car UI application."""

from __future__ import annotations

import os
import logging
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

from apps.carUi.car_ui_composition import CarUiComposition
from apps.carUi.car_ui_dependencies import CarUiDependencies
from apps.carUi.car_ui_menu_catalog import create_car_ui_menu_pages
from apps.carUi.screens.tk_car_ui_screen_factory import TkCarUiScreenFactory
from frontends.tk.menu import MenuRenderer
from ui.menu import MenuTile
from frontends.tk.runtime import apply_fullscreen
from apps.common.uiTheme.uiTheme import (
    CAR_UI_THEME,
    STATUS_BAR_THEME,
    TOP_BAR_THEME,
)
from frontends.tk.system import StatusBarPanel, TopBarPanel, VolumePanel
from ui.screen_navigator_if import ScreenNavigatorIf
from ui.screen_ui_if import ScreenId, ScreenUiIf
from ui.ui_action import UiAction
from ui.ui_event_handler_if import UiEventHandlerIf
from ui.ui_if import UiIf


CAR_UI_LOGO_PATH = Path(__file__).parent / "assets" / "openroadcode.png"
LOGGER = logging.getLogger(__name__)


class CarUiFrontend(tk.Tk, UiIf, UiEventHandlerIf, ScreenNavigatorIf):
    """Render the Car UI shell and delegate application wiring."""

    def __init__(
        self,
        dependencies: CarUiDependencies,
        title: str = "OpenRoadCode",
    ) -> None:
        super().__init__()
        self._closed = False
        self._initialized = False
        self._active_route_id: ScreenId | None = None
        self._navigation_history: list[ScreenId] = []
        self._runtime = dependencies.runtime
        self._weather_controller = dependencies.runtime.weather_controller
        self.title(title)
        self._app_icon: tk.PhotoImage | None = None
        self._apply_app_icon()

        self.theme = CAR_UI_THEME
        self.colors = self.theme["colors"]
        self.layout = self.theme["layout"]
        geometry = self._get_ui_geometry()
        self.compact_ui = self._geometry_is_compact(geometry)
        self.style = self.theme["profiles"][
            "compact" if self.compact_ui else "normal"
        ]

        self.geometry(geometry)
        self.minsize(*self.theme["window"]["minimum_size"])
        if os.getenv(self.theme["window"]["fullscreen_env"], "0") == "1":
            apply_fullscreen(self)
        self.configure(bg=self.colors["app_bg"])

        self._build_shell()
        self.menu_renderer = MenuRenderer(
            content_frame=self.content_frame,
            colors=self.colors,
            layout=self.layout,
            style=self.style,
            on_tile_clicked=self._run_callback,
        )
        self.composition = CarUiComposition(
            self,
            dependencies,
            TkCarUiScreenFactory(
                self,
                compact_ui=self.compact_ui,
                create_menu_tile=self.create_menu_tile,
                show_main_menu=self.show_main_menu,
                show_menu=self.show_menu,
            ),
        )
        self.show_main_menu()

        self.bind("<Escape>", self._toggle_fullscreen)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _apply_app_icon(self) -> None:
        """Apply the OpenRoadCode logo to the Tk window and desktop shell."""
        try:
            icon = tk.PhotoImage(file=str(CAR_UI_LOGO_PATH))
            self.iconphoto(True, icon)
            self._app_icon = icon
        except (OSError, tk.TclError):
            self._app_icon = None

    def initialize(self) -> bool:
        """Start composed services and make the frontend ready to run.

        @return True unless the frontend has already been closed.
        """
        if self._closed:
            return False
        if not self._initialized:
            self.composition.lifecycle.start()
            self._runtime.start_background_apps()
            self._initialized = True
            if self._weather_controller is not None:
                threading.Thread(
                    target=self._refresh_weather_data,
                    name="weather-data-preload",
                    daemon=True,
                ).start()
        return True

    def _refresh_weather_data(self) -> None:
        controller = self._weather_controller
        if controller is None:
            return
        try:
            controller.refresh_if_stale(120)
        except Exception:
            LOGGER.exception("Weather data background refresh failed")

    def run(self) -> None:
        """Run the Tk event loop until shutdown."""
        self.mainloop()

    def shutdown(self) -> None:
        """Perform idempotent frontend shutdown."""
        self.close()

    def close(self) -> None:
        """Stop composed services and destroy the Tk application."""
        if self._closed:
            return
        self._closed = True
        try:
            self.composition.lifecycle.stop()
        finally:
            try:
                self.quit()
            finally:
                try:
                    self.destroy()
                except tk.TclError:
                    pass

    def handle_ui_action(self, action: UiAction) -> None:
        """Route a semantic action through the application composition.

        @param action Toolkit-independent UI action to route.
        """
        self.composition.handle_ui_action(action)

    @property
    def empty_value(self) -> str:
        """Return the theme placeholder for unavailable compact values.

        @return Configured placeholder text.
        """
        return self.layout["empty_value"]

    def dispatch_ui(self, callback: Callable[[], None]) -> None:
        """Queue work on the Tk event-loop thread.

        @param callback Work to invoke on the Tk thread.
        """
        self.after(0, callback)

    @property
    def screen_parent(self) -> tk.Misc:
        """Return the container for navigable screen content.

        @return Tk content frame owned by the application shell.
        """
        return self.content_frame

    def activate_screen(self, screen: ScreenUiIf) -> None:
        """Make a screen the active semantic action target.

        @param screen Screen to activate.
        """
        self.composition.activate_screen(screen)

    def clear_screen_content(self) -> None:
        """Destroy widgets belonging to the previous destination."""
        for child in self.content_frame.winfo_children():
            child.destroy()

    @property
    def active_screen_id(self) -> ScreenId | None:
        """Return the current route identifier.

        @return Active route identifier, or None on the main menu.
        """
        return self._active_route_id

    def show_screen(self, screen_id: ScreenId) -> None:
        """Navigate to a registered screen while recording history.

        @param screen_id Destination screen identifier.
        """
        if self._active_route_id is not None:
            self._navigation_history.append(self._active_route_id)
        self._active_route_id = screen_id
        try:
            self.composition.open_route(screen_id.value)
        except Exception:
            self._active_route_id = (
                self._navigation_history.pop()
                if self._navigation_history
                else None
            )
            raise

    def go_back(self) -> bool:
        """Navigate to the previous route.

        @return True when a history entry was opened.
        """
        if not self._navigation_history:
            return False
        previous = self._navigation_history.pop()
        self._active_route_id = previous
        self.composition.open_route(previous.value)
        return True

    def go_home(self) -> None:
        """Clear navigation history and display the main menu."""
        self._navigation_history.clear()
        self.show_main_menu()

    def set_screen_title(self, title: str) -> None:
        """Set the active shell title.

        @param title User-visible screen title.
        """
        self.top_bar.set_title(title)

    def set_screen_back_action(self, action: Callable[[], None]) -> None:
        """Configure and show the active screen's back action.

        @param action Callback invoked by the back control.
        """
        self.top_bar.set_back_action(action)
        self.top_bar.show_back_button()

    def set_screen_status(self, message: str) -> None:
        """Set the active screen's status message.

        @param message User-visible status text.
        """
        self.status_bar.set_status(message)

    def schedule_ui_callback(
        self,
        delay_ms: int,
        callback: Callable[[], None],
    ) -> object:
        """Schedule delayed work on the Tk event loop.

        @param delay_ms Non-negative delay in milliseconds.
        @param callback Work to invoke after the delay.
        @return Tk callback identifier usable for cancellation.
        """
        return self.after(delay_ms, callback)

    def cancel_ui_callback(self, callback_id: object) -> None:
        """Cancel a pending Tk callback.

        @param callback_id Identifier returned by schedule_ui_callback().
        """
        self.after_cancel(callback_id)

    def show_main_menu(self) -> None:
        """Display the configured home menu and reset shell state."""
        if hasattr(self, "composition"):
            self.composition.activate_screen(None)
        self._active_route_id = None
        self.clear_screen_content()
        self.top_bar.set_title("OpenRoadCode")
        self.top_bar.set_back_action(self.show_main_menu)
        self.top_bar.hide_back_button()
        self._show_menu_page("main")
        self.status_bar.set_status("Ready")

    def show_menu(self, menu_key: str) -> None:
        """Display an application submenu.

        @param menu_key Stable key of the menu page to display.
        """
        self.composition.activate_screen(None)
        self._active_route_id = ScreenId(menu_key)
        titles = {"radio": "Radio", "media": "Media", "gauges": "Gauges"}
        title = titles.get(menu_key, "OpenRoadCode")
        self.clear_screen_content()
        self.top_bar.set_title(title)
        self.top_bar.set_back_action(self.show_main_menu)
        self.top_bar.show_back_button()
        self._show_menu_page(menu_key)
        self.status_bar.set_status(titles.get(menu_key, menu_key.title()))

    def _build_shell(self) -> None:
        container = tk.Frame(self, bg=self.colors["app_bg"])
        container.pack(fill=self.layout["fill_both"], expand=True)
        self.top_bar = TopBarPanel(
            container,
            compact_ui=self.compact_ui,
            theme=TOP_BAR_THEME,
            logo_path=CAR_UI_LOGO_PATH,
            on_back=self.show_main_menu,
            right_accessory_factory=self._create_volume_panel,
            on_settings=self._handle_settings,
            on_power=self._handle_power_off,
        )
        self.top_bar.pack(
            fill=self.layout["fill_horizontal"],
            side=self.layout["side_top"],
        )
        self.content_frame = tk.Frame(container, bg=self.colors["app_bg"])
        self.content_frame.pack(
            fill="both",
            expand=True,
            padx=self.style["content_padx"],
            pady=self.style["content_pady"],
        )
        self.status_bar = StatusBarPanel(
            container,
            theme=STATUS_BAR_THEME,
            compact_ui=self.compact_ui,
            initial_status="Ready",
        )
        self.status_bar.pack(
            fill=self.layout["fill_horizontal"],
            side=self.layout["side_bottom"],
        )

    def _create_volume_panel(self, parent: tk.Widget) -> tk.Widget:
        self.volume_panel = VolumePanel(
            parent,
            theme=TOP_BAR_THEME,
            compact_ui=self.compact_ui,
            indicator_steps=self.layout["volume_steps"],
        )
        return self.volume_panel

    def _show_menu_page(self, menu_key: str) -> None:
        pages = create_car_ui_menu_pages()
        self.menu_renderer.show_page(pages.get(menu_key, pages["main"]))

    def create_menu_tile(
        self,
        parent: tk.Widget,
        key: str,
        label: str,
        subtitle: str,
        detail: str,
    ) -> tk.Frame:
        """Create a Car UI menu tile for an application-specific screen.

        @param parent Parent Tk widget.
        @param key Stable destination key.
        @param label Primary tile label.
        @param subtitle Secondary tile label.
        @param detail Supplemental tile detail.
        @return Constructed tile frame.
        """
        return self.menu_renderer.create_tile(
            parent=parent,
            tile=MenuTile(
                key=key,
                title=label,
                subtitle=subtitle,
                detail=detail,
            ),
        )

    def _run_callback(self, key: str) -> None:
        try:
            self.show_screen(ScreenId(key))
        except Exception as exc:
            self.status_bar.set_status(f"Navigation error in {key}: {exc}")
            print(f"[UI] Navigation error for {key}: {exc}")

    def _handle_power_off(self) -> None:
        self.composition.system_control_manager.power_off()

    def _handle_settings(self) -> None:
        if self.composition.has_route("settings"):
            self.composition.open_route("settings")
        else:
            self.status_bar.set_status("Settings panel is not available")

    def _toggle_fullscreen(self, _event: object = None) -> None:
        current = bool(self.attributes("-fullscreen"))
        self.attributes("-fullscreen", not current)
        mode = "enabled" if not current else "disabled"
        self.status_bar.set_status(f"Fullscreen {mode}")

    def _get_ui_geometry(self) -> str:
        window = self.theme["window"]
        explicit = os.getenv(window["geometry_env"])
        if explicit:
            return explicit
        profile = os.getenv(
            window["profile_env"], window["default_profile"]
        ).strip().lower()
        return window["profiles"].get(profile, window["default_geometry"])

    def _geometry_is_compact(self, geometry: str) -> bool:
        try:
            size = geometry.split("+", 1)[0]
            width_text, height_text = size.lower().split("x", 1)
            width, height = int(width_text), int(height_text)
            window = self.theme["window"]
            return (
                width <= window["compact_max_width"]
                or height <= window["compact_max_height"]
            )
        except (TypeError, ValueError):
            return False
