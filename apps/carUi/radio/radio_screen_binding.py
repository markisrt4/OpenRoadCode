from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

from frontends.tk.radio import RadioPanel, RadioPanelConfig
from apps.carUi.radio.radio_session_config import RadioSessionConfig
from apps.carUi.radio.radio_session_controller import RadioSessionController
from apps.launchers.app_launcher_if import AppLauncherIf
from controllers.radio.radio_controller_if import RadioControllerIf
from controllers.radio.radio_types import RadioPreset
from apps.common.uiTheme import RADIO_PANEL_THEME


@dataclass(frozen=True)
class RadioPanelBinding:
    """Bind a radio session controller to its passive Tk panel."""
    session: RadioSessionController
    panel: RadioPanel


def create_radio_screen_binding(
    *,
    parent: tk.Widget,
    radio_controller: RadioControllerIf,
    radio_app_launcher: AppLauncherIf,
    panel_config: RadioPanelConfig,
    remote_display: str,
    set_status: Optional[Callable[[str], None]] = None,
    on_frequency_changed: Optional[Callable[[int], None]] = None,
    on_preset_pressed: Optional[Callable[[RadioPreset], None]] = None,
    presets_per_bank: int = 6,
) -> RadioPanelBinding:
    """Create one radio session presenter and its passive Tk panel.

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
        session_config=RadioSessionConfig(
            key=panel_config.key,
            title=panel_config.title,
            default_step_hz=panel_config.default_step_hz,
        ),
        remote_display=remote_display,
        set_status=set_status,
        on_preset_pressed=on_preset_pressed,
    )
    panel = RadioPanel(
        parent=parent,
        panel_config=panel_config,
        theme=RADIO_PANEL_THEME,
        on_frequency_changed=on_frequency_changed,
        presets_per_bank=presets_per_bank,
    )
    session.set_radio_ui(panel)
    return RadioPanelBinding(session=session, panel=panel)
