"""Presentation-only platform selection for the navigation map."""

from dataclasses import replace
import tkinter as tk
from ui.navigation.map_platform_if import MapPlatform, MapPlatformControlIf, MapPlatformState
from ui.theme import ThemeBundle


class MapPlatformBar(tk.Frame):
    def __init__(self, parent, *, handler: MapPlatformControlIf, theme: ThemeBundle, platforms=(MapPlatform.MAPLIBRE, MapPlatform.EARTH)):
        ui = theme.ui
        super().__init__(parent, bg=ui.surface_alt)
        self._buttons = {}
        for platform in platforms:
            button = tk.Button(self, text=platform.value, relief=tk.FLAT,
                               font=("Sans", 9, "bold"), bg=ui.control_background,
                               fg=ui.control_text, activebackground=ui.control_active,
                               command=lambda selected=platform: handler.request_platform(selected))
            button.pack(side=tk.LEFT, padx=3, pady=2)
            self._buttons[platform] = button
        self._chase = tk.Button(self, text="Chase view", relief=tk.FLAT,
            font=("Sans", 9, "bold"), bg=ui.control_background, fg=ui.control_text,
            command=handler.request_chase)
        if MapPlatform.EARTH in platforms:
            self._chase.pack(side=tk.LEFT, padx=3, pady=2)
        self._status = tk.Label(self, bg=ui.surface_alt, fg=ui.text_muted,
                                font=("Sans", 8), anchor="w", justify=tk.LEFT)
        self._status.pack(fill=tk.X, expand=True, padx=4)
        self._status.bind("<Configure>", lambda event: self._status.configure(wraplength=max(1, event.width)))

    def set_state(self, state: MapPlatformState) -> None:
        self._chase.configure(state=tk.NORMAL if state.active is MapPlatform.EARTH
                              and not state.busy else tk.DISABLED)
        for platform, button in self._buttons.items():
            button.configure(relief=tk.SUNKEN if platform is state.requested else tk.FLAT,
                             state=tk.DISABLED if state.busy else tk.NORMAL)
        self._status.configure(text=state.status)


class MapPlatformToggle(tk.Button):
    """One user-facing Map/Terrain control for the existing navigation toolbar."""

    def __init__(self, parent, *, handler: MapPlatformControlIf, theme: ThemeBundle, on_state=None):
        self._on_state = on_state
        self._handler = handler
        self._state = MapPlatformState()
        ui = theme.ui
        super().__init__(parent, text='Map ⇄', command=self._toggle,
            relief=tk.FLAT, font=('Sans',8,'bold'), width=8,
            bg=ui.control_background, fg=ui.control_text,
            activebackground=ui.control_active, padx=4, pady=3)
        self.set_state(handler.state)

    def _toggle(self):
        if not self._state.busy:
            target = MapPlatform.MAPLIBRE if self._state.active is MapPlatform.CESIUM else MapPlatform.CESIUM
            previous = self._state
            self.set_state(replace(previous,requested=target,busy=True))
            if self._on_state is not None:
                self._on_state(self._state)
            try:
                self._handler.request_platform(target)
            except Exception:
                self.set_state(previous)
                if self._on_state is not None:
                    self._on_state(previous)
                raise

    def set_state(self, state: MapPlatformState):
        self._state = state
        self.configure(text='Loading…' if state.busy else 'Terrain ⇄' if state.active is MapPlatform.CESIUM else 'Map ⇄',
                       state=tk.DISABLED if state.busy else tk.NORMAL,
                       relief=tk.SUNKEN if state.active is MapPlatform.CESIUM else tk.FLAT)
