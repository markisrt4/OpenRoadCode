# SPDX-License-Identifier: MIT
"""Receiver orchestration; workers never touch a GUI or its native host widget."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import Lock, RLock

from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.sdr.sdrpp_control import SDRPPControl
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from ui.radio.rf_radio_if import (
    AircraftPresentation, RadioAction, RadioApplication, RadioHost, RadioNativeSurface,
    RadioRequest, RfProfile, RfRadioState, RfRadioUi,
)


class ReceiverSession:
    """Use a composition-owned serial executor for shared receiver/native operations.

    Retirement is immediate. Cleanup remains on the same serial executor as launch,
    so an in-flight embed finishes and detaches before another session can launch.
    """

    def __init__(self, radio: RadioProfileController, control: SDRPPControl,
                 telemetry: SDRTelemetryMonitor, application: RadioApplication,
                 aircraft: AircraftPresentation, surface: RadioNativeSurface, *,
                 display: str, run_work: Callable[[Callable[[], None]], None],
                 run_ui: Callable[[Callable[[], None]], None],
                 on_close: Callable[[], None] = lambda: None) -> None:
        self._radio = radio
        self._control = control
        self._telemetry = telemetry
        self._application = application
        self._aircraft = aircraft
        self._surface = surface
        self._display = display
        self._run_work = run_work
        self._run_ui = run_ui
        self._on_close = on_close
        self._lock = Lock()
        self._native_lock = RLock()
        self._generation = 0
        self._closed = False
        self._active = True
        self._refresh_pending = False
        self._view: RfRadioUi | None = None
        self._host: RadioHost | None = None
        self._native_view = "none"
        self._state = RfRadioState(radio.state, self._profiles())

    def _profiles(self) -> tuple[RfProfile, ...]:
        return tuple(RfProfile(p.key, p.label, p.group, p.presets) for p in self._radio.catalog.profiles)

    def bind(self, view: RfRadioUi) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Receiver session is closed")
            self._view = view
        view.set_radio_state(self._state)

    def request(self, request: RadioRequest) -> None:
        with self._lock:
            if self._closed or not self._active:
                return
            generation = self._generation
            if request.action is RadioAction.REFRESH:
                if self._refresh_pending:
                    return
                self._refresh_pending = True
        def work() -> None:
            try:
                if not self._current(generation):
                    return
                if request.host is not None:
                    self._host = request.host
                self._perform(request, generation)
            except (OSError, RuntimeError, ValueError) as error:
                message = str(error)
                if request.action in (RadioAction.LAUNCH, RadioAction.ADSB):
                    try:
                        with self._native_lock:
                            self._cleanup_native()
                    except (OSError, RuntimeError, ValueError) as cleanup_error:
                        message += f"; cleanup: {cleanup_error}"
                self._state = replace(self._state, loading=False, error=message)
            finally:
                if request.action is RadioAction.REFRESH:
                    with self._lock:
                        self._refresh_pending = False
                self._publish(generation)
        self._run_work(work)

    def _current(self, generation: int) -> bool:
        with self._lock:
            return self._active and not self._closed and self._generation == generation

    def _publish(self, generation: int) -> None:
        state = self._state
        def deliver() -> None:
            if self._current(generation) and self._view is not None:
                self._view.set_radio_state(state)
        self._run_ui(deliver)

    def _launch(self, request: RadioRequest, generation: int) -> None:
        host = self._host
        if host is None:
            raise ValueError("A native host is required")
        with self._native_lock:
            if not self._current(generation):
                return
            self._cleanup_native()
        self._state = replace(self._state, loading=True, error="")
        self._publish(generation)
        if request.action is RadioAction.ADSB:
            self._application.relinquish_for_adsb()
            with self._native_lock:
                if not self._current(generation):
                    return
                self._aircraft.assert_available()
                self._aircraft.set_preferred_color_scheme(request.color_scheme)
                self._aircraft.configure_browser_window(position=(host.x, host.y), size=(host.width, host.height))
                self._aircraft.launch(self._display)
                self._native_view = "adsb"
            process_id, window_class = 0, "OpenRoadCodeADSB"
        else:
            self._application.present()
            if not self._current(generation):
                return
            if self._application.fullscreen:
                self._state = replace(self._state, view="fullscreen", loading=False)
                return
            process_id = self._application.window_process_id(timeout_seconds=2.0)
            window_class = "sdrpp"
        with self._native_lock:
            if not self._current(generation):
                self._cleanup_native()
                return
            self._native_view = "adsb" if window_class == "OpenRoadCodeADSB" else "sdrpp"
            self._surface.embed(process_id, host.window_id, host.width, host.height,
                                window_class=window_class, relax_size_hints=window_class == "sdrpp",
                                cancelled=lambda: not self._current(generation))
            if not self._current(generation):
                self._cleanup_native()
                return
            self._state = replace(self._state, view=self._native_view, loading=False)


    def _perform(self, request: RadioRequest, generation: int) -> None:
        action = request.action
        if action in (RadioAction.LAUNCH, RadioAction.ADSB):
            self._launch(request, generation)
            if self._current(generation) and request.action is RadioAction.LAUNCH:
                self._read_controls()
            return
        if action is RadioAction.RESIZE:
            if self._host is not None:
                with self._native_lock:
                    if self._current(generation):
                        self._surface.resize(self._host.width, self._host.height)
            return
        if action is RadioAction.REFRESH:
            if self._native_view == "sdrpp":
                self._state = replace(self._state, telemetry=self._telemetry.read_state(
                    include_rds=self._radio.active_profile_key == "fm_radio"))
            return
        if self._native_view == "adsb":
            self._launch(RadioRequest(RadioAction.LAUNCH), generation)
            if not self._current(generation):
                return
        if action is RadioAction.PROFILE:
            self._radio.select_profile(request.key)
        elif action is RadioAction.PRESET and request.preset is not None:
            if self._radio.active_profile_key != request.key:
                self._radio.select_profile(request.key)
            self._radio.tune_preset(request.preset)
        elif action is RadioAction.ADD_PRESET:
            self._radio.catalog.add_user_preset(request.key, label=request.label,
                                               frequency_hz=self._radio.state.frequency_hz)
        elif action is RadioAction.THEME:
            self._control.set_theme(request.key)
        else:
            operations: dict[RadioAction, Callable[[], object]] = {
                RadioAction.PREVIOUS: self._radio.previous_preset,
                RadioAction.NEXT: self._radio.next_preset,
                RadioAction.TUNE_DOWN: self._radio.tune_down,
                RadioAction.TUNE_UP: self._radio.tune_up,
                RadioAction.WATERFALL: self._control.toggle_waterfall,
                RadioAction.BANDPLAN: self._control.toggle_bandplan,
                RadioAction.FFT_HOLD: self._control.toggle_fft_hold,
                RadioAction.AUTO_RANGE: self._control.auto_range,
            }
            operations[action]()
        self._state = replace(self._state, station=self._radio.state,
                              profiles=self._profiles(), error="")
        self._read_controls()

    def _read_controls(self) -> None:
        try:
            self._state = replace(self._state, waterfall=self._control.waterfall_visible(),
                                  bandplan=self._control.bandplan_visible(),
                                  fft_hold=self._control.fft_hold_enabled(), themes=self._control.themes())
        except (OSError, RuntimeError, ValueError):
            pass

    def _cleanup_native(self) -> None:
        try:
            if self._host is not None:
                self._surface.detach(self._host.parent_id)
        finally:
            try:
                if self._native_view == "adsb":
                    self._aircraft.stop(self._display)
            finally:
                try:
                    self._surface.clear()
                finally:
                    self._native_view = "none"

    def deactivate(self) -> None:
        with self._lock:
            if not self._active:
                return
            self._active = False
            self._generation += 1
            self._view = None
        # Detach before Tk destroys the host. A launch already in progress must
        # finish first; generation retirement prevents any later reattachment.
        with self._native_lock:
            self._cleanup_native()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self.deactivate()
        finally:
            self._on_close()
