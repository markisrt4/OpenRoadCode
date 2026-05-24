from __future__ import annotations

from typing import Callable, Optional

from modules.radio.radio_controller import RadioController
from modules.radio.radio_types import RadioPreset

from apps.launchers.app_launcher_if import AppLauncherIf
from apps.carUi.radio.radio_panel_config import RadioPanelConfig
from apps.carUi.radio.radio_status_formatter import format_frequency


class RadioPanelController:
    def __init__(
        self,
        radio_controller: RadioController,
        radio_app_launcher: AppLauncherIf,
        panel_config: RadioPanelConfig,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
        on_preset_pressed: Optional[Callable[[RadioPreset], None]] = None,
        update_radio_status: Optional[
            Callable[[Optional[int], Optional[RadioPreset]], None]
        ] = None,
        on_frequency_tuned: Optional[
            Callable[[int, Optional[RadioPreset]], None]
        ] = None,
    ) -> None:
        self.radio_controller = radio_controller
        self.radio_app_launcher = radio_app_launcher
        self.panel_config = panel_config
        self.remote_display = remote_display
        self.set_status = set_status
        self.on_preset_pressed = on_preset_pressed
        self.update_radio_status = update_radio_status
        self.on_frequency_tuned = on_frequency_tuned

        self.radio_running = False

    def toggle_radio_app(self) -> None:
        try:
            running = self.radio_app_launcher.toggle(
                remote_display=self.remote_display,
                set_status=self.set_status,
            )

            if running:
                self._status(f"{self.panel_config.title} app launched")
            else:
                self.radio_running = False
                self._status(f"{self.panel_config.title} app stopped")

        except Exception as exc:
            self._status(f"{self.panel_config.title} app toggle failed: {exc}")
            print(f"[{self.panel_config.key}] app toggle failed: {exc}")

    def toggle_radio(self) -> None:
        try:
            if self.radio_running:
                self.radio_controller.stop()
                self.radio_running = False
                self._status(f"{self.panel_config.title} radio stopped")
                return

            if hasattr(self.radio_app_launcher, "wait_for_rigctl"):
                self._status(f"{self.panel_config.title} waiting for SDR++ rigctl...")
                self.radio_app_launcher.wait_for_rigctl(set_status=self.set_status)

            self.radio_controller.start()
            self.radio_running = True

            frequency = getattr(self.radio_controller, "current_frequency_hz", None)

            self._update_status(frequency_hz=frequency)

            if frequency is not None:
                self._notify_frequency_tuned(frequency_hz=frequency, preset=None)

            self._status(f"{self.panel_config.title} radio started")

        except OSError as exc:
            self.radio_running = False
            self._status(f"{self.panel_config.title} radio unavailable: {exc}")
            print(f"[{self.panel_config.key}] radio unavailable: {exc}")

        except Exception as exc:
            self.radio_running = False
            self._status(f"{self.panel_config.title} radio start failed: {exc}")
            print(f"[{self.panel_config.key}] radio start failed: {exc}")

    def tune_preset(self, preset: RadioPreset) -> None:
        try:
            self.radio_controller.tune_preset(preset)

            self._notify_frequency_tuned(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

            if self.on_preset_pressed:
                self.on_preset_pressed(preset)

            self._update_status(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

            self._status(
                f"{self.panel_config.title}: {preset.label} "
                f"({format_frequency(preset.frequency_hz)})"
            )

        except OSError as exc:
            self._status(f"{self.panel_config.title} preset failed: {exc}")
            print(f"[{self.panel_config.key}] preset failed: {exc}")

    def frequency_up(self) -> None:
        try:
            frequency = self.radio_controller.frequency_up()

            self._notify_frequency_tuned(
                frequency_hz=frequency,
                preset=None,
            )

            self._update_status(frequency_hz=frequency)
            self._status(f"{self.panel_config.title}: {format_frequency(frequency)}")

        except OSError as exc:
            self._status(f"{self.panel_config.title} tune up failed: {exc}")
            print(f"[{self.panel_config.key}] tune up failed: {exc}")

    def frequency_down(self) -> None:
        try:
            frequency = self.radio_controller.frequency_down()

            self._notify_frequency_tuned(
                frequency_hz=frequency,
                preset=None,
            )

            self._update_status(frequency_hz=frequency)
            self._status(f"{self.panel_config.title}: {format_frequency(frequency)}")

        except OSError as exc:
            self._status(f"{self.panel_config.title} tune down failed: {exc}")
            print(f"[{self.panel_config.key}] tune down failed: {exc}")

    def next_preset(self) -> None:
        try:
            preset = self.radio_controller.next_preset()

            self._notify_frequency_tuned(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

            self._update_status(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )
            self._status(f"{self.panel_config.title}: {preset.label}")

        except (OSError, ValueError) as exc:
            self._status(f"{self.panel_config.title} next preset failed: {exc}")
            print(f"[{self.panel_config.key}] next preset failed: {exc}")

    def previous_preset(self) -> None:
        try:
            preset = self.radio_controller.previous_preset()

            self._notify_frequency_tuned(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )

            self._update_status(
                frequency_hz=preset.frequency_hz,
                preset=preset,
            )
            self._status(f"{self.panel_config.title}: {preset.label}")

        except (OSError, ValueError) as exc:
            self._status(f"{self.panel_config.title} previous preset failed: {exc}")
            print(f"[{self.panel_config.key}] previous preset failed: {exc}")

    def _update_status(
        self,
        frequency_hz: Optional[int] = None,
        preset: Optional[RadioPreset] = None,
    ) -> None:
        if self.update_radio_status:
            self.update_radio_status(frequency_hz, preset)

    def _notify_frequency_tuned(
        self,
        frequency_hz: int,
        preset: Optional[RadioPreset] = None,
    ) -> None:
        if self.on_frequency_tuned:
            self.on_frequency_tuned(frequency_hz, preset)

    def _status(self, message: str) -> None:
        if self.set_status:
            self.set_status(message)
