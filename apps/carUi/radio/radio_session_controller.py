from __future__ import annotations

from typing import Callable, Optional

from apps.carUi.radio.radio_session_config import RadioSessionConfig
from apps.carUi.radio.radio_session_state import RadioSessionState
from ui.radio.radio_formatter import format_frequency
from apps.launchers.app_launcher_if import AppLauncherIf
from controllers.radio.radio_controller_if import RadioControllerIf
from controllers.radio.radio_types import RadioPreset
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from ui.radio import (
    ModulationType,
    PlaybackRequestHandlerIf,
    PresetRequestHandlerIf,
    RadioApplicationRequestHandlerIf,
    RadioMode as UiRadioMode,
    RadioPreset as UiRadioPreset,
    RadioRefreshRequestHandlerIf,
    RadioUiIf,
    StationRequestHandlerIf,
    TunedSignal,
    TuningRequestHandlerIf,
)


class RadioSessionController(
    PresetRequestHandlerIf,
    PlaybackRequestHandlerIf,
    StationRequestHandlerIf,
    TuningRequestHandlerIf,
    RadioApplicationRequestHandlerIf,
    RadioRefreshRequestHandlerIf,
):
    """Coordinate a radio domain controller, launcher, and panel state."""
    def __init__(
        self,
        radio_controller: RadioControllerIf,
        radio_app_launcher: AppLauncherIf,
        session_config: RadioSessionConfig,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
        on_preset_pressed: Optional[Callable[[RadioPreset], None]] = None,
    ) -> None:
        self._radio = radio_controller
        self._launcher = radio_app_launcher
        self._config = session_config
        self._remote_display = remote_display
        self._set_status = set_status
        self._on_preset_pressed = on_preset_pressed
        self._radio_ui: RadioUiIf | None = None
        self._telemetry_monitor = SDRTelemetryMonitor(radio_controller)

        self._receiver_started = False
        self._active_preset: RadioPreset | None = None

    @property
    def presets(self) -> tuple[RadioPreset, ...]:
        """Return configured presets as an immutable tuple."""
        return tuple(self._radio.presets)

    def set_radio_ui(self, radio_ui: RadioUiIf | None) -> None:
        """Attach a radio UI and wire all of its semantic requests."""
        self._radio_ui = radio_ui
        if radio_ui is None:
            return
        radio_ui.set_preset_request_handler(self)
        radio_ui.set_playback_request_handler(self)
        radio_ui.set_station_request_handler(self)
        radio_ui.set_tuning_request_handler(self)
        radio_ui.set_application_request_handler(self)
        radio_ui.set_refresh_request_handler(self)
        radio_ui.clear_presets()
        for preset in self.presets:
            radio_ui.add_preset(self._to_ui_preset(preset))

    def report_ready(self) -> None:
        """Publish a ready status message for this radio session."""
        self._status(f"{self._config.title} ready")

    def toggle_radio_app(self) -> None:
        """Toggle the external radio application."""
        try:
            running = self._launcher.toggle(
                remote_display=self._remote_display,
                set_status=self._set_status,
            )

            if running:
                self._status(f"{self._config.title} app launched")
            else:
                self._receiver_started = False
                self._status(f"{self._config.title} app stopped")

            self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._report_failure("app toggle", exc)

    def request_toggle_radio_application(self) -> None:
        self.toggle_radio_app()

    def request_radio_refresh(self) -> None:
        self.refresh_state(include_telemetry=True)

    def toggle_radio(self) -> RadioSessionState:
        """Start or stop the receiver and return its resulting state."""
        try:
            if self._receiver_started:
                self._radio.stop()
                self._receiver_started = False
                self._status(f"{self._config.title} radio stopped")
                return self.refresh_state(include_telemetry=False)

            wait_for_rigctl = getattr(self._launcher, "wait_for_rigctl", None)
            if callable(wait_for_rigctl):
                self._status(f"{self._config.title} waiting for SDR++ rigctl...")
                wait_for_rigctl(set_status=self._set_status)

            self._radio.start()
            self._receiver_started = True
            self._active_preset = self._match_preset(self._current_frequency())
            self._status(f"{self._config.title} radio started")
            return self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._receiver_started = False
            self._report_failure("radio start", exc)
            return self.refresh_state(include_telemetry=False)

    def tune_preset(self, preset: RadioPreset) -> RadioSessionState:
        """Tune a preset and return the resulting panel state."""
        try:
            tuned = self._radio.tune_preset(preset)
            self._active_preset = tuned

            if self._on_preset_pressed is not None:
                self._on_preset_pressed(tuned)

            self._status(
                f"{self._config.title}: {tuned.label} "
                f"({format_frequency(tuned.frequency_hz)})"
            )
            return self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._report_failure("preset", exc)
            return self.refresh_state(include_telemetry=False)

    def frequency_up(self) -> RadioSessionState:
        """Step frequency upward and return the resulting state."""
        return self._adjust_frequency("tune up", self._radio.frequency_up)

    def frequency_down(self) -> RadioSessionState:
        """Step frequency downward and return the resulting state."""
        return self._adjust_frequency("tune down", self._radio.frequency_down)

    def next_preset(self) -> RadioSessionState:
        """Tune the next preset and return the resulting state."""
        return self._cycle_preset("next preset", self._radio.next_preset)

    def previous_preset(self) -> RadioSessionState:
        """Tune the previous preset and return the resulting state."""
        return self._cycle_preset("previous preset", self._radio.previous_preset)

    def request_preset(self, preset_index: int) -> None:
        """Handle a UI request for a zero-based preset index."""
        presets = self.presets
        if 0 <= preset_index < len(presets):
            self.tune_preset(presets[preset_index])

    def request_play(self) -> None:
        """Handle a UI request to start radio playback."""
        if not self._receiver_started:
            self.toggle_radio()

    def request_pause(self) -> None:
        """Handle a UI request to pause radio playback."""
        if self._receiver_started:
            self.toggle_radio()

    def request_next_station(self) -> None:
        """Handle a UI request for the next configured station."""
        self._cycle_preset("next station", self._radio.next_station)

    def request_previous_station(self) -> None:
        """Handle a UI request for the previous configured station."""
        self._cycle_preset("previous station", self._radio.previous_station)

    def request_tune_up(self) -> None:
        """Handle a UI request for one upward frequency step."""
        self.frequency_up()

    def request_tune_down(self) -> None:
        """Handle a UI request for one downward frequency step."""
        self.frequency_down()

    def refresh_state(
        self,
        include_telemetry: bool = True,
        publish: bool = True,
    ) -> RadioSessionState:
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
        state = RadioSessionState(
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

        if publish:
            self._publish_ui_state(state)

        return state

    def _publish_ui_state(self, state: RadioSessionState) -> None:
        radio_ui = self._radio_ui
        if radio_ui is None:
            return
        radio_ui.set_receiver_active(state.receiver_started)
        radio_ui.set_active_preset(state.preset_index)
        if state.frequency_hz is None:
            radio_ui.set_signal(None)
            return

        mode = self._current_ui_mode()
        radio_ui.set_signal(
            TunedSignal(
                frequency_hz=state.frequency_hz,
                mode=mode,
                snr_db=self._numeric(state.snr),
                signal_strength_dbfs=self._numeric(state.signal_strength),
                rds_text=state.rds,
            )
        )

    def _current_ui_mode(self) -> UiRadioMode:
        source = (
            self._active_preset.mode
            if self._active_preset is not None
            else getattr(self._radio, "current_mode", None)
            or getattr(self._radio, "default_mode", None)
        )
        name = str(getattr(source, "name", "FM")).upper()
        modulation = ModulationType.__members__.get(name, ModulationType.FM)
        return UiRadioMode(
            modulation=modulation,
            bandwidth_hz=int(getattr(source, "bandwidth", 0)),
            step_hz=int(getattr(source, "step_hz", self._config.default_step_hz)),
        )

    @staticmethod
    def _to_ui_preset(preset: RadioPreset) -> UiRadioPreset:
        name = preset.mode.name.upper()
        modulation = ModulationType.__members__.get(name, ModulationType.FM)
        return UiRadioPreset(
            label=preset.label,
            frequency_hz=preset.frequency_hz,
            mode=UiRadioMode(
                modulation=modulation,
                bandwidth_hz=preset.mode.bandwidth,
                step_hz=preset.mode.step_hz,
            ),
        )

    @staticmethod
    def _numeric(value: float | str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _adjust_frequency(
        self,
        operation: str,
        action: Callable[[], int],
    ) -> RadioSessionState:
        try:
            frequency_hz = action()
            self._active_preset = self._match_preset(frequency_hz)
            self._status(
                f"{self._config.title}: {format_frequency(frequency_hz)}"
            )
            return self.refresh_state(include_telemetry=False)
        except Exception as exc:
            self._report_failure(operation, exc)
            return self.refresh_state(include_telemetry=False)

    def _cycle_preset(
        self,
        operation: str,
        action: Callable[[], RadioPreset],
    ) -> RadioSessionState:
        try:
            preset = action()
            self._active_preset = preset

            if self._on_preset_pressed is not None:
                self._on_preset_pressed(preset)

            self._status(f"{self._config.title}: {preset.label}")
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
        self._status(f"{self._config.title} {operation} failed: {exc}")
        print(f"[{self._config.key}] {operation} failed: {exc}")

    def _status(self, message: str) -> None:
        if self._set_status is not None:
            self._set_status(message)
