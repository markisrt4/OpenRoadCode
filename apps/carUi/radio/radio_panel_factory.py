from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

from apps.carUi.radio.radio_panel import RadioPanel
from apps.carUi.radio.radio_panel_config import RadioPanelConfig
from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.launchers.app_launcher_if import AppLauncherIf
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_types import RadioPreset


@dataclass(frozen=True)
class RadioPanelBinding:
    """Bind a radio session controller to its passive Tk panel."""
    session: RadioSessionController
    panel: RadioPanel


def create_radio_panel_binding(
    *,
    parent: tk.Widget,
    radio_controller: RadioController,
    radio_app_launcher: AppLauncherIf,
    panel_config: RadioPanelConfig,
    remote_display: str,
    set_status: Optional[Callable[[str], None]] = None,
    on_frequency_changed: Optional[Callable[[int], None]] = None,
    on_preset_pressed: Optional[Callable[[RadioPreset], None]] = None,
    presets_per_bank: int = 6,
) -> RadioPanelBinding:
    """Create one radio session controller and its passive Tk panel.

    @param parent Parent widget for the panel.
    @param radio_controller Domain controller used for tuning.
    @param radio_app_launcher Launcher for the external radio application.
    @param panel_config Labels and tuning defaults for the panel.
    @param remote_display Display used by the external application.
    @param set_status Optional status-message callback.
    @param on_frequency_changed Optional frequency-change callback.
    @param on_preset_pressed Optional preset-selection callback.
    @param presets_per_bank Number of presets displayed per page.
    @return Newly connected session and panel.
    """

    session = RadioSessionController(
        radio_controller=radio_controller,
        radio_app_launcher=radio_app_launcher,
        panel_config=panel_config,
        remote_display=remote_display,
        set_status=set_status,
        on_preset_pressed=on_preset_pressed,
    )
    panel = RadioPanel(
        parent=parent,
        controller=session,
        panel_config=panel_config,
        on_frequency_changed=on_frequency_changed,
        presets_per_bank=presets_per_bank,
    )
    return RadioPanelBinding(session=session, panel=panel)
