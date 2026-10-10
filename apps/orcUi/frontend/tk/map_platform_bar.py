"""Presentation-only platform selection for the navigation map."""

import tkinter as tk
from ui.navigation.map_platform_if import MapPlatform, MapPlatformControlIf, MapPlatformState
from ui.theme import ThemeBundle


class MapPlatformBar(tk.Frame):
    def __init__(self, parent, *, handler: MapPlatformControlIf, theme: ThemeBundle):
        ui = theme.ui
        super().__init__(parent, bg=ui.surface_alt)
        self._buttons = {}
        for platform in MapPlatform:
            button = tk.Button(self, text=platform.value, relief=tk.FLAT,
                               font=("Sans", 9, "bold"), bg=ui.control_background,
                               fg=ui.control_text, activebackground=ui.control_active,
                               command=lambda selected=platform: handler.request_platform(selected), highlightthickness=0, bd=0)
            button.pack(side=tk.LEFT, padx=3, pady=2)
            self._buttons[platform] = button
        self._chase = tk.Button(self, text="Chase view", relief=tk.FLAT,
            font=("Sans", 9, "bold"), bg=ui.control_background, fg=ui.control_text,
            command=handler.request_chase, highlightthickness=0, bd=0)
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
