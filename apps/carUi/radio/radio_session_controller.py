from __future__ import annotations

from typing import Callable, Optional

from apps.carUi.radio.radio_panel_config import RadioPanelConfig
from apps.carUi.radio.radio_panel_state import RadioPanelState
from apps.carUi.radio.radio_status_formatter import format_frequency
from apps.launchers.app_launcher_if import AppLauncherIf
from controllers.radio.radio_controller import RadioController
from controllers.radio.radio_types import RadioPreset
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor


class RadioSessionController:
    """Coordinate a radio domain controller, launcher, and panel state."""
    def __init__(
        self,
        radio_controller: RadioController,
        radio_app_launcher: AppLauncherIf,
        panel_config: RadioPanelConfig,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
        on_preset_pressed: Optional[Callable[[RadioPreset], None]] = None,
    ) -> None:
        self._radio = radio_controller
        self._launcher = radio_app_launcher
        self._panel_config = panel_config
        self._remote_display = remote_display
        self._set_status = set_status
        self._on_preset_pressed = on_preset_pressed
        self._on_state_changed: Optional[Callable[[RadioPanelState], None]] = None
        self._telemetry_monitor = SDRTelemetryMonitor(radio_controller)

        self._receiver_started = False
        self._active_preset: RadioPreset | None = None

    @property
    def presets(self) -> tuple[RadioPreset, ...]:
        """Return configured presets as an immutable tuple."""
        return tuple(self._radio.presets)

    @property
    def panel_config(self) -> RadioPanelConfig:
        """Return presentation configuration for the bound panel."""
        return self._panel_config

    def set_state_listener(
        self,
        listener: Optional[Callable[[RadioPanelState], None]],
    ) -> None:
        """Set or clear the callback receiving refreshed panel state."""
        self._on_state_changed = listener

    def report_ready(self) -> None:
        """Publish a ready status message for this radio session."""
        self._status(f"{self._panel_config.title} ready")

    def toggle_radio_app(self) -> None:
        """Toggle the external radio application."""
        try:
            running = self._launcher.toggle(
                remote_display=self._remote_display,
                set_status=self._set_status,
            )

            if running:
                self._status(f"{self._panel_config.title} app launched")
            else:
                self._receiver_started = False
                self._status(f"{self._panel_config.title} app stopped")

            self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._report_failure("app toggle", exc)

    def toggle_radio(self) -> RadioPanelState:
        """Start or stop the receiver and return its resulting state."""
        try:
            if self._receiver_started:
                self._radio.stop()
                self._receiver_started = False
                self._status(f"{self._panel_config.title} radio stopped")
                return self.refresh_state(include_telemetry=False)

            wait_for_rigctl = getattr(self._launcher, "wait_for_rigctl", None)
            if callable(wait_for_rigctl):
                self._status(f"{self._panel_config.title} waiting for SDR++ rigctl...")
                wait_for_rigctl(set_status=self._set_status)

            self._radio.start()
            self._receiver_started = True
            self._active_preset = self._match_preset(self._current_frequency())
            self._status(f"{self._panel_config.title} radio started")
            return self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._receiver_started = False
            self._report_failure("radio start", exc)
            return self.refresh_state(include_telemetry=False)

    def tune_preset(self, preset: RadioPreset) -> RadioPanelState:
        """Tune a preset and return the resulting panel state."""
        try:
            tuned = self._radio.tune_preset(preset)
            self._active_preset = tuned

            if self._on_preset_pressed is not None:
                self._on_preset_pressed(tuned)

            self._status(
                f"{self._panel_config.title}: {tuned.label} "
                f"({format_frequency(tuned.frequency_hz)})"
            )
            return self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._report_failure("preset", exc)
            return self.refresh_state(include_telemetry=False)

    def frequency_up(self) -> RadioPanelState:
        """Step frequency upward and return the resulting state."""
        return self._adjust_frequency("tune up", self._radio.frequency_up)

    def frequency_down(self) -> RadioPanelState:
        """Step frequency downward and return the resulting state."""
        return self._adjust_frequency("tune down", self._radio.frequency_down)

    def next_preset(self) -> RadioPanelState:
        """Tune the next preset and return the resulting state."""
        return self._cycle_preset("next preset", self._radio.next_preset)

    def previous_preset(self) -> RadioPanelState:
        """Tune the previous preset and return the resulting state."""
        return self._cycle_preset("previous preset", self._radio.previous_preset)

    def refresh_state(
        self,
        include_telemetry: bool = True,
        publish: bool = True,
    ) -> RadioPanelState:
        """Read receiver telemetry, notify the listener, and return state."""
        frequency_hz = self._current_frequency()
        matched_preset = self._match_preset(frequency_hz)
        if matched_preset is not None:
            self._active_preset = matched_preset
        elif frequency_hz is not None:
            self._active_preset = None

        signal_strength: float | str | None = None
        snr: float | str | None = None
        rds: str | None = None

        if include_telemetry:
            try:
                mode_name = self._current_mode_name()
                telemetry = self._telemetry_monitor.read(
                    include_rds=(mode_name == "WFM")
                )
                if telemetry.frequency_hz is not None:
                    frequency_hz = telemetry.frequency_hz
                    self._active_preset = self._match_preset(frequency_hz)
                signal_strength = telemetry.signal
                snr = telemetry.snr
                rds = telemetry.rds
            except (OSError, RuntimeError, ValueError):
                pass

        preset_index = self._preset_index(self._active_preset)
        state = RadioPanelState(
            receiver_started=self._receiver_started,
            frequency_hz=frequency_hz,
            mode_name=self._current_mode_name(),
            active_preset=self._active_preset,
            preset_index=preset_index,
            preset_count=len(self.presets),
            signal_strength=signal_strength,
            snr=snr,
            rds=rds,
        )

        if publish and self._on_state_changed is not None:
            self._on_state_changed(state)

        return state

    def _adjust_frequency(
        self,
        operation: str,
        action: Callable[[], int],
    ) -> RadioPanelState:
        try:
            frequency_hz = action()
            self._active_preset = self._match_preset(frequency_hz)
            self._status(
                f"{self._panel_config.title}: {format_frequency(frequency_hz)}"
            )
            return self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._report_failure(operation, exc)
            return self.refresh_state(include_telemetry=False)

    def _cycle_preset(
        self,
        operation: str,
        action: Callable[[], RadioPreset],
    ) -> RadioPanelState:
        try:
            preset = action()
            self._active_preset = preset

            if self._on_preset_pressed is not None:
                self._on_preset_pressed(preset)

            self._status(f"{self._panel_config.title}: {preset.label}")
            return self.refresh_state(include_telemetry=False)

        except Exception as exc:
            self._report_failure(operation, exc)
            return self.refresh_state(include_telemetry=False)

    def _current_frequency(self) -> int | None:
        frequency_hz = getattr(self._radio, "current_frequency_hz", None)
        if frequency_hz is not None:
            return int(frequency_hz)

        get_frequency = getattr(self._radio, "get_frequency", None)
        if callable(get_frequency):
            try:
                return int(get_frequency())
            except (OSError, RuntimeError, TypeError, ValueError):
                return None

        return None

    def _current_mode_name(self) -> str | None:
        if self._active_preset is not None:
            return self._active_preset.mode.name

        current_mode = getattr(self._radio, "current_mode", None)
        if current_mode is not None:
            return getattr(current_mode, "name", None)

        default_mode = getattr(self._radio, "default_mode", None)
        return getattr(default_mode, "name", None)

    def _match_preset(self, frequency_hz: int | None) -> RadioPreset | None:
        if frequency_hz is None:
            return None

        for preset in self.presets:
            if preset.frequency_hz == frequency_hz:
                return preset

        return None

    def _preset_index(self, preset: RadioPreset | None) -> int | None:
        if preset is None:
            return None

        try:
            return self.presets.index(preset)
        except ValueError:
            return None

    def _report_failure(self, operation: str, exc: Exception) -> None:
        self._status(f"{self._panel_config.title} {operation} failed: {exc}")
        print(f"[{self._panel_config.key}] {operation} failed: {exc}")

    def _status(self, message: str) -> None:
        if self._set_status is not None:
            self._set_status(message)
