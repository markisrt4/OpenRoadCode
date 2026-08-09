"""Narrow services injected into Car UI-specific screens."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Protocol

from apps.carUi.radio.radio_screen_binding import RadioPanelBinding
from apps.launchers.app_launcher_if import AppLauncherIf
from controllers.radio.radio_controller_if import RadioControllerIf
from controllers.radio.radio_types import RadioPreset
from frontends.tk.radio import RadioPanelConfig


MenuTileFactory = Callable[
    [tk.Widget, str, str, str, str],
    tk.Frame,
]


class RadioScreenBindingFactoryIf(Protocol):
    """Create a connected radio session and its frontend panel."""

    def __call__(
        self,
        *,
        parent: tk.Widget,
        radio_controller: RadioControllerIf,
        radio_app_launcher: AppLauncherIf,
        panel_config: RadioPanelConfig,
        remote_display: str,
        set_status: Callable[[str], None] | None = None,
        on_frequency_changed: Callable[[int], None] | None = None,
        on_preset_pressed: Callable[[RadioPreset], None] | None = None,
        presets_per_bank: int = 6,
    ) -> RadioPanelBinding:
        """Create a radio panel and its connected application session.

        The parent, panel configuration, and returned panel are specific to
        the selected frontend. Controllers and callbacks remain semantic.
        """
        ...
