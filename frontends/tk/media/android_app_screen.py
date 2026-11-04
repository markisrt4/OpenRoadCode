# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Landscape map/app presentation sharing the hosted X11 surface lifecycle."""
import tkinter as tk
from collections.abc import Callable

from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from ui.navigation.android_app_view_if import AndroidAppViewState, AndroidAppViewRequestHandlerIf
from ui.navigation.map_runtime_if import MapRuntimeIf, MapPresentationRequestHandlerIf
from ui.navigation.map_platform_if import MapPlatformControlIf
from ui.navigation.navigation_experience_if import NavigationExperienceRequestHandlerIf
from frontends.tk.navigation_experience_controls import NavigationExperienceControls


class AndroidAppScreen(BrowserMediaScreen):
    """Split evenly by default; expand without restarting the Android surface."""

    def __init__(self, *args, map_runtime: MapRuntimeIf,
                 map_platform: MapPlatformControlIf,
                 requests: AndroidAppViewRequestHandlerIf,
                 breadcrumb: Callable[[str], None],
                 experience_handler: NavigationExperienceRequestHandlerIf | None = None,
                 map_presentation: MapPresentationRequestHandlerIf | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._map_runtime = map_runtime
        self._experience_handler = experience_handler
        self._experience_controls = None
        self._map_platform = map_platform
        self._requests = requests
        self._breadcrumb = breadcrumb
        self._map_presentation = map_presentation
        self._map_refresh_jobs = []
        self._state = AndroidAppViewState()
        self._map_host = None
        self._map_job = None
        self._map_running = False
        self._map_generation = 0
        self._expand_button = None
        self._toolbar = None
        self._name_label = None
        self._back_button = None
        self._close_button = None
        self._destination_buttons = []
        self._waze_mode_button = None
        self._surface_resize_job = None
        self._surface_generation = 0
        # App-first Waydroid presentation requests immersive status mode itself.
        # Trim the nested Weston panel and Android navigation area automatically.
        self._vertical_crop = (32, 48)

    def present(self, state: AndroidAppViewState) -> None:
        self._state = state
        self._title = state.app_name
        # Cropping only affects the nested viewport, not Android permissions.
        if self._visible:
            self._name_label.configure(text=state.app_name)
            self._host.set_screen_title(state.app_name)
            self._breadcrumb(state.app_name)
            self._apply_layout()
            # Grid changes are deferred by Tk. Flush them before sizing the
            # compositor, then reapply after native output configuration settles.
            if self._surface_resize_job is not None:
                self._host.cancel_ui_callback(self._surface_resize_job)
                self._surface_resize_job = None
            self._surface_generation += 1
            generation = self._surface_generation
            self._root.update_idletasks()
            self._resize_android_surface()
            self._surface_resize_job = self._host.schedule_ui_callback(150, lambda: self._settled_resize(generation))

    def _settled_resize(self, generation):
        if generation != self._surface_generation or not self._visible:
            return
        self._surface_resize_job = None
        self._resize_android_surface()

    def _resize_android_surface(self):
        if self._visible and self._browser_host is not None and self._browser_host.winfo_exists():
            self._embedder.set_vertical_crop(*self._vertical_crop)
            self._embedder.resize(self._browser_host.winfo_width(), self._browser_host.winfo_height())

    def _button_style(self):
        ui = self._theme_provider().ui if self._theme_provider is not None else None
        return dict(bg=ui.control_background if ui else '#101b23',
                    fg=ui.control_text if ui else '#ffffff',
                    activebackground=ui.control_active if ui else '#20313e',
                    activeforeground=ui.text if ui else '#ffffff',
                    relief=tk.FLAT, bd=0, highlightthickness=0,
                    font=('Sans', 9, 'bold'), padx=12, pady=6, cursor='hand2')

    def _destination_button_style(self, key):
        style = self._button_style()
        if self._theme_provider is not None:
            ui = self._theme_provider().ui
            style['fg'] = ui.accent_primary if key == 'home' else ui.accent_warning
        return style

    def show(self) -> None:
        self.hide()
        self._host.activate_screen(self)
        self._host.clear_screen_content()
        self._host.set_screen_title(self._title)
        self._host.set_screen_back_action(self._back_action)
        self._breadcrumb(self._state.app_name)
        self._visible = True
        root = tk.Frame(self._host.screen_parent, bg=self._background())
        root.pack(fill=tk.BOTH, expand=True)
        root.grid_rowconfigure(1, weight=1)
        self._root = root
        toolbar = tk.Frame(root, bg=self._background())
        self._toolbar = toolbar
        toolbar.grid(row=0, column=0, columnspan=3, sticky='ew')
        self._back_button = tk.Button(toolbar, text='MAP' if self._state.navigation_mode_controls else '‹ BACK TO MAP',
                                     command=self._back_action, **self._button_style())
        self._back_button.pack(side=tk.LEFT, padx=4, pady=4)
        shared_navigation = self._state.navigation_mode_controls and self._experience_handler is not None
        if shared_navigation:
            self._back_button.pack_forget()
        if self._state.navigation_mode_controls:
            style = self._button_style()
            style['bg'] = self._theme_provider().ui.control_active if self._theme_provider is not None else '#20313e'
            self._waze_mode_button = tk.Button(toolbar, text='WAZE', state=tk.DISABLED,
                                               disabledforeground='#ffffff', **style)
            self._waze_mode_button.pack(side=tk.LEFT, padx=0, pady=4)
            if shared_navigation:
                self._waze_mode_button.pack_forget()
        foreground = self._theme_provider().ui.text if self._theme_provider is not None else 'white'
        self._name_label = tk.Label(toolbar, text=self._state.app_name, bg=self._background(), fg=foreground)
        if not self._state.navigation_mode_controls:
            self._name_label.pack(side=tk.LEFT, padx=8)
        if self._state.can_navigate_saved_destinations:
            for key, label in (('home', '⌂ HOME'), ('work', '▣ WORK')):
                button = tk.Button(toolbar, text=label,
                    command=lambda key=key: self._requests.request_navigate_saved_destination(key),
                    **self._destination_button_style(key))
                button.pack(side=tk.LEFT, padx=4, pady=4)
                self._destination_buttons.append(button)
                if shared_navigation:
                    button.pack_forget()
        self._expand_button = tk.Button(toolbar, command=self._requests.request_toggle_android_app_expanded,
                                        **self._button_style())
        self._expand_button.pack(side=tk.RIGHT, padx=4, pady=4)
        if self._close_action is not None:
            self._close_button = tk.Button(toolbar, text='CLOSE WAZE', command=self._close_action,
                                           **self._button_style())
            self._close_button.pack(side=tk.RIGHT, padx=4, pady=4)
            if shared_navigation:
                self._close_button.pack_forget()
        if not self._state.can_split:
            self._expand_button.pack_forget()
        self._map_host = tk.Frame(root, bg=self._background())
        self._map_host.bind('<Configure>', self._resize_map)
        self._browser_host = tk.Frame(root, bg=self._background())
        self._browser_host.bind('<Configure>', self._on_browser_host_resize)
        if shared_navigation:
            self._experience_controls = NavigationExperienceControls(toolbar,
                drawer_parent=root, drawer_row=1, drawer_column=2,
                handler=self._experience_handler, theme=self._theme_provider())
            self._experience_controls.pack(fill=tk.X, expand=True)
            self._experience_controls.set_surface_loading(True)
        self._apply_layout()
        self._launch_job = self._host.schedule_ui_callback(1, self._launch_and_embed)
        self._requests.request_set_android_app_visible(True)

    def _launch_and_embed(self):
        try:
            super()._launch_and_embed()
        finally:
            if self._experience_controls is not None:
                self._experience_controls.set_surface_loading(False)

    def _apply_layout(self):
        if self._root is None:
            return
        if self._state.expanded:
            self._map_host.grid_remove()
            self._root.grid_columnconfigure(0, weight=0, minsize=0, uniform='')
            self._root.grid_columnconfigure(1, weight=1, uniform='')
            self._stop_map()
            self._expand_button.configure(text='SPLIT VIEW')
        else:
            self._root.grid_columnconfigure(0, weight=1, uniform='panes')
            self._root.grid_columnconfigure(1, weight=1, uniform='panes')
            self._map_host.grid(row=1, column=0, sticky='nsew', padx=(0, 2))
            if not self._map_running and self._map_job is None:
                generation = self._map_generation
                self._map_job = self._host.schedule_ui_callback(1, lambda: self._start_map(generation))
            self._expand_button.configure(text='FULL SCREEN APP')
        self._browser_host.grid(row=1, column=1, sticky='nsew')

    def _start_map(self, generation=None):
        if generation is not None and generation != self._map_generation:
            return
        self._map_job = None
        if not self._visible or self._state.expanded or self._map_host is None:
            return
        try:
            self._map_host.update_idletasks()
            self._resize_map()
            self._map_runtime.launch(int(self._map_host.winfo_id()))
            self._map_running = True
            if self._map_presentation is not None:
                current = self._map_generation
                self._replay_map(current)
                for delay in (300, 700, 1200):
                    self._map_refresh_jobs.append(self._host.schedule_ui_callback(
                        delay, lambda generation=current: self._replay_map(generation)))
        except (OSError, RuntimeError) as error:
            self._map_running = False
            self._map_runtime.stop()
            self._host.set_screen_status(f'Map unavailable: {error}')

    def _replay_map(self, generation):
        if self._visible and self._map_running and generation == self._map_generation:
            self._map_presentation.request_replay_map_presentation()

    def _resize_map(self, _event=None):
        if self._map_host is not None and self._visible and not self._state.expanded:
            self._map_platform.resize(max(1, self._map_host.winfo_width()),
                                      max(1, self._map_host.winfo_height()),
                                      int(self._map_host.winfo_toplevel().winfo_id()))

    def _stop_map(self):
        self._map_generation += 1
        for job in self._map_refresh_jobs:
            self._host.cancel_ui_callback(job)
        self._map_refresh_jobs.clear()
        if self._map_job is not None:
            self._host.cancel_ui_callback(self._map_job)
            self._map_job = None
        if self._map_running:
            self._map_running = False
            self._map_runtime.stop()

    def hide(self):
        if self._experience_controls is not None:
            self._experience_controls.destroy()
            self._experience_controls = None
        self._requests.request_set_android_app_visible(False)
        self._surface_generation += 1
        if self._surface_resize_job is not None:
            self._host.cancel_ui_callback(self._surface_resize_job)
            self._surface_resize_job = None
        self._stop_map()
        super().hide()
        self._experience_controls = None
        self._map_host = None
        self._expand_button = None
        self._toolbar = None
        self._name_label = None
        self._back_button = None
        self._close_button = None
        self._destination_buttons = []
        self._waze_mode_button = None

    def set_theme_mode(self, mode):
        super().set_theme_mode(mode)
        self._map_runtime.set_theme(mode)
        if self._visible:
            for widget in (self._toolbar, self._map_host, self._name_label):
                widget.configure(bg=self._background())
            if self._theme_provider is not None:
                self._name_label.configure(fg=self._theme_provider().ui.text)
            for button in (self._back_button, self._expand_button, self._close_button):
                if button is not None:
                    button.configure(**self._button_style())
            for key, button in zip(('home', 'work'), self._destination_buttons):
                button.configure(**self._destination_button_style(key))
            if self._waze_mode_button is not None:
                style = self._button_style()
                style['bg'] = self._theme_provider().ui.control_active
                self._waze_mode_button.configure(**style)
            if self._experience_controls is not None:
                self._experience_controls.set_theme(self._theme_provider())
