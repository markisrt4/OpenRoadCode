# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Radio group and preset menu behavior for the ORC radio panel."""

import tkinter as tk
from functools import partial
from tkinter import simpledialog

from ui.radio.rf_radio_if import RadioAction, RadioRequest, RfProfile
from ui.radio.radio_profiles import RadioProfilePreset
from .radio_presentation_frame import RadioPresentationFrame
from .shell_metrics import FONT_CONTROL

MAIN_GROUPS = (
    ("FM", "♫ FM ▾"),
    ("WEATHER", "☁ WEATHER ▾"),
    ("AIR", "✈ AIR ▾"),
    ("HAM", "⌁ HAM ▾"),
    ("SCANNER", "⌁ SCANNER ▾"),
)


class RadioGroupMenuMixin(RadioPresentationFrame):
    """Own radio group selection and preset menus."""

    def _build_group_bar(self) -> None:
        ui = self._theme.ui
        for name, label in MAIN_GROUPS:
            command = partial(self._show_group_menu, name)
            button = tk.Button(
                self._groups,
                text=label,
                command=command,
                bg=ui.surface,
                fg=ui.text,
                activebackground=ui.control_background,
                activeforeground=ui.accent_success,
                relief=tk.FLAT,
                bd=0,
                font=("Sans", FONT_CONTROL, "bold"),
                padx=9,
                pady=7,
            )
            button.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self._group_buttons[name] = button
        self._controls_button = tk.Button(
            self._groups,
            text="☰ CONTROLS",
            command=self._toggle_drawer,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            relief=tk.FLAT,
            bd=0,
            font=("Sans", FONT_CONTROL, "bold"),
            padx=12,
            pady=7,
        )
        self._controls_button.pack(side=tk.RIGHT)
        self._paint_groups()

    def _show_group_menu(self, group: str) -> None:
        self._active_group = group
        self._paint_groups()
        button = self._group_buttons[group]
        ui = self._theme.ui
        menu = tk.Menu(
            self,
            tearoff=False,
            bg=ui.surface,
            fg=ui.text,
            activebackground=ui.control_background,
            activeforeground=ui.accent_success,
            bd=1,
            relief=tk.FLAT,
            font=("Sans", 11),
        )
        profiles = tuple(p for p in self._state.profiles if p.group == group)
        for profile in profiles:
            if len(profiles) == 1:
                self._add_profile_presets(menu, profile)
            else:
                submenu = tk.Menu(
                    menu,
                    tearoff=False,
                    bg=ui.surface,
                    fg=ui.text,
                    activebackground=ui.control_background,
                    activeforeground=ui.accent_success,
                    font=("Sans", 11),
                )
                self._add_profile_presets(submenu, profile)
                menu.add_cascade(label=profile.label, menu=submenu)
        if group == "AIR":
            if profiles:
                menu.add_separator()
            menu.add_command(label="✈ ADS-B Aircraft Map", command=self._show_adsb)
        if profiles:
            menu.add_separator()
            menu.add_command(
                label="＋ Add Current Preset", command=partial(self._add_current_preset, group)
            )
        self._popup_menu(menu, button)

    def _add_profile_presets(self, menu: tk.Menu, profile: RfProfile) -> None:
        if not profile.presets:
            menu.add_command(
                label=profile.label, command=partial(self._select_profile, profile.key)
            )
            return
        for preset in profile.presets:
            marker = "★ " if preset.user_defined else ""
            menu.add_command(
                label=f"{marker}{preset.label}",
                command=partial(self._select_preset, profile, preset),
            )

    def _select_profile(self, profile_key: str) -> None:
        self._session.request(RadioRequest(RadioAction.PROFILE, key=profile_key))

    def _select_preset(self, profile: RfProfile, preset: RadioProfilePreset) -> None:
        self._session.request(RadioRequest(RadioAction.PRESET, key=profile.key, preset=preset))
        self._active_group = profile.group
        self._paint_groups()

    def _add_current_preset(self, group: str) -> None:
        profiles = tuple(p for p in self._state.profiles if p.group == group)
        if not profiles:
            return
        profile = (
            next(p for p in profiles if p.key == self._state.station.profile_key)
            if self._state.station.profile_key in {p.key for p in profiles}
            else profiles[0]
        )
        state = self._state.station
        label = simpledialog.askstring(
            "Add radio preset", "Preset name:", initialvalue=state.label, parent=self
        )
        if label:
            self._session.request(RadioRequest(RadioAction.ADD_PRESET, key=profile.key, label=label))

    @staticmethod
    def _popup_menu(menu: tk.Menu, button: tk.Button) -> None:
        x = button.winfo_rootx()
        y = button.winfo_rooty() + button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _paint_groups(self) -> None:
        ui = self._theme.ui
        parent_active = self._active_group.split(":", 1)[0]
        for name, button in self._group_buttons.items():
            active = name == parent_active
            button.configure(
                fg=ui.accent_success if active else ui.text,
                bg=ui.surface_alt if active else ui.surface,
                activebackground=ui.control_background,
                activeforeground=ui.accent_success,
            )
