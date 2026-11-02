# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Landscape map/app presentation sharing the hosted X11 surface lifecycle."""
import tkinter as tk
from collections.abc import Callable

from frontends.tk.media.browser_media_screen import BrowserMediaScreen
from ui.navigation.android_app_view_if import AndroidAppViewState, AndroidAppViewRequestHandlerIf
from ui.navigation.map_runtime_if import MapRuntimeIf
from ui.navigation.map_platform_if import MapPlatformControlIf


class AndroidAppScreen(BrowserMediaScreen):
    """Split evenly by default; expand without restarting the Android surface."""

    def __init__(self, *args, map_runtime: MapRuntimeIf,
                 map_platform: MapPlatformControlIf,
                 requests: AndroidAppViewRequestHandlerIf,
                 breadcrumb: Callable[[str], None], **kwargs):
        super().__init__(*args, **kwargs)
        self._map_runtime = map_runtime
        self._map_platform = map_platform
        self._requests = requests
        self._breadcrumb = breadcrumb
        self._state = AndroidAppViewState()
        self._map_host = None
        self._map_job = None
        self._map_running = False
        self._map_generation = 0
        self._expand_button = None
        self._toolbar = None
        self._name_label = None
        self._trim_button = None

    def present(self, state: AndroidAppViewState) -> None:
        self._state = state
        self._title = state.app_name
        # Default VM geometry: Weston panel + Android status bar, then navbar.
        # This only clips the nested surface and never changes Android policies.
        self._vertical_crop = (56, 48) if state.trim_android_frame else (0, 0)
        if self._visible:
            self._name_label.configure(text=state.app_name)
            self._host.set_screen_title(state.app_name)
            self._breadcrumb(state.app_name)
            self._apply_layout()
            self._embedder.set_vertical_crop(*self._vertical_crop)
            self._embedder.resize(self._browser_host.winfo_width(), self._browser_host.winfo_height())

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
        toolbar.grid(row=0, column=0, columnspan=2, sticky='ew')
        tk.Button(toolbar, text='Back to map', command=self._back_action).pack(side=tk.LEFT, padx=4, pady=4)
        foreground = self._theme_provider().ui.text if self._theme_provider is not None else 'white'
        self._name_label = tk.Label(toolbar, text=self._state.app_name, bg=self._background(), fg=foreground)
        self._name_label.pack(side=tk.LEFT, padx=8)
        self._expand_button = tk.Button(toolbar, command=self._requests.request_toggle_android_app_expanded)
        self._expand_button.pack(side=tk.RIGHT, padx=4, pady=4)
        self._trim_button = tk.Button(toolbar, command=self._requests.request_toggle_android_frame_trim)
        self._trim_button.pack(side=tk.RIGHT, padx=4, pady=4)
        self._map_host = tk.Frame(root, bg=self._background())
        self._map_host.bind('<Configure>', self._resize_map)
        self._browser_host = tk.Frame(root, bg=self._background())
        self._browser_host.bind('<Configure>', self._on_browser_host_resize)
        self._apply_layout()
        self._launch_job = self._host.schedule_ui_callback(1, self._launch_and_embed)

    def _apply_layout(self):
        if self._root is None:
            return
        self._trim_button.configure(text='Show Android frame' if self._state.trim_android_frame else 'Trim Android frame')
        if self._state.expanded:
            self._map_host.grid_remove()
            self._root.grid_columnconfigure(0, weight=0, minsize=0, uniform='')
            self._root.grid_columnconfigure(1, weight=1, uniform='')
            self._stop_map()
            self._expand_button.configure(text='Split view')
        else:
            self._root.grid_columnconfigure(0, weight=1, uniform='panes')
            self._root.grid_columnconfigure(1, weight=1, uniform='panes')
            self._map_host.grid(row=1, column=0, sticky='nsew', padx=(0, 2))
            if not self._map_running and self._map_job is None:
                generation = self._map_generation
                self._map_job = self._host.schedule_ui_callback(1, lambda: self._start_map(generation))
            self._expand_button.configure(text='Expand app')
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
        except (OSError, RuntimeError) as error:
            self._map_runtime.stop()
            self._host.set_screen_status(f'Map unavailable: {error}')

    def _resize_map(self, _event=None):
        if self._map_host is not None and self._visible and not self._state.expanded:
            self._map_platform.resize(max(1, self._map_host.winfo_width()),
                                      max(1, self._map_host.winfo_height()),
                                      int(self._map_host.winfo_toplevel().winfo_id()))

    def _stop_map(self):
        self._map_generation += 1
        if self._map_job is not None:
            self._host.cancel_ui_callback(self._map_job)
            self._map_job = None
        if self._map_running:
            self._map_running = False
            self._map_runtime.stop()

    def hide(self):
        self._stop_map()
        super().hide()
        self._map_host = None
        self._expand_button = None
        self._toolbar = None
        self._name_label = None
        self._trim_button = None

    def set_theme_mode(self, mode):
        super().set_theme_mode(mode)
        self._map_runtime.set_theme(mode)
        if self._visible:
            for widget in (self._toolbar, self._map_host, self._name_label):
                widget.configure(bg=self._background())
            if self._theme_provider is not None:
                self._name_label.configure(fg=self._theme_provider().ui.text)
