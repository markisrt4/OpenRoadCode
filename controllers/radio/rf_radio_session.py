# SPDX-License-Identifier: MIT
"""Receiver orchestration; workers never touch a GUI or its native host widget."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import Event, Lock, RLock, Thread
from time import sleep
import json
import urllib.request
import urllib.error

from controllers.radio.radio_profile_controller import RadioProfileController
from controllers.sdr.sdrpp_control import SDRPPControl
from controllers.sdr.sdr_telemetry_monitor import SDRTelemetryMonitor
from ui.radio.sdrforge_spectrum_if import SpectrumSourceIf, SpectrumPresentationIf
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
                 on_close: Callable[[], None] = lambda: None,
                 spectrum_source: SpectrumSourceIf | None = None) -> None:
        self._spectrum_source = spectrum_source
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
        self._scan_cancel = Event()
        self._owns_receiver = False
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
        if self._spectrum_source is not None:
            self._spectrum_source.start()
        view.set_radio_state(self._state)

    def refresh_spectrum(self) -> None:
        """Transfer latest immutable spectrum state to the UI, never the transport."""
        with self._lock:
            if self._closed or not self._active or self._spectrum_source is None:
                return
            view = self._view
        if view is None:
            return
        receiver = self._spectrum_source.latest_receiver()
        if receiver is not None:
            # Spectrum telemetry may omit RDS fields between decoder updates.
            # Preserve the last decoded text only while tuned to the same station.
            previous = self._state.telemetry
            if (receiver.frequency_hz == previous.frequency_hz
                    and not (receiver.radio_text or receiver.station_name or receiver.rds)):
                receiver = replace(receiver, radio_text=previous.radio_text,
                                   station_name=previous.station_name, rds=previous.rds)
            # Telemetry updates signal/RDS only. Rigctl refresh owns station state.
            self._state = replace(self._state, telemetry=receiver)
            view.set_radio_state(self._state)
        snapshot = self._spectrum_source.latest_spectrum()
        if snapshot is not None and isinstance(view, SpectrumPresentationIf):
            view.set_spectrum_presentation(snapshot)

    def request(self, request: RadioRequest) -> None:
        if request.action is RadioAction.STOP_SCAN:
            self._scan_cancel.set()
            return
        if request.action is RadioAction.SCAN:
            self._scan_cancel.clear()
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
        if action in (RadioAction.START_RECEIVER, RadioAction.STOP_RECEIVER):
            endpoint = "start" if action is RadioAction.START_RECEIVER else "stop"
            with urllib.request.urlopen(
                urllib.request.Request(
                    f"http://127.0.0.1:5570/v1/receiver/{endpoint}",
                    data=b"", method="POST",
                ), timeout=6.0,
            ) as response:
                if response.status not in (200, 202):
                    raise RuntimeError(f"SDRForge receiver {endpoint} failed")
            self._owns_receiver = action is RadioAction.START_RECEIVER
            self._state = replace(self._state,
                                  receiver_running=action is RadioAction.START_RECEIVER,
                                  error="")
            return
        if action in (RadioAction.PLAY, RadioAction.PAUSE):
            endpoint = "unmute" if action is RadioAction.PLAY else "mute"
            request_url = f"http://127.0.0.1:5570/v1/audio/{endpoint}"
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(request_url, data=b"", method="POST"),
                    timeout=6.0,
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"SDRForge {endpoint} returned {response.status}")
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"SDRForge {endpoint} failed: HTTP {exc.code}") from exc
            self._state = replace(self._state, playing=action is RadioAction.PLAY,
                                  error="")
            return
        if action is RadioAction.SCAN:
            self._scan(generation)
            return
        if action is RadioAction.RESIZE:
            if self._host is not None:
                with self._native_lock:
                    if self._current(generation):
                        self._surface.resize(self._host.width, self._host.height)
            return
        if action is RadioAction.REFRESH:
            # Rigctl is the authoritative receiver state, including external
            # changes made by Android. Do not retune during a refresh.
            if self._native_view != "adsb":
                try:
                    with urllib.request.urlopen(
                        "http://127.0.0.1:5570/v1/receiver", timeout=1.5,
                    ) as response:
                        status = json.load(response)
                    with urllib.request.urlopen(
                        "http://127.0.0.1:5570/v1/audio", timeout=1.5,
                    ) as response:
                        audio_status = json.load(response)
                    self._state = replace(
                        self._state, receiver_running=bool(status.get("running", False)),
                        playing=not bool(audio_status.get("muted", False)),
                    )
                except (OSError, ValueError, RuntimeError):
                    pass
                self._state = replace(self._state, station=self._radio.refresh())
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
        elif action is RadioAction.TUNE_FREQUENCY:
            if request.frequency_hz is None:
                raise ValueError("tune frequency request requires frequency_hz")
            self._radio.tune_frequency(request.frequency_hz)
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

    def _scan(self, generation: int) -> None:
        """Sweep the configured band and find local signal-strength peaks."""
        band = self._radio.scan_range
        if band is None:
            raise ValueError("No frequency range configured for this band")
        low, high, step = band
        count = (high - low) // step + 1
        if count > 3000:
            raise ValueError("Scan exceeds 3000 channels; narrow the range")
        original = self._radio.state.frequency_hz
        samples: list[tuple[int, float]] = []
        self._state = replace(self._state, scanning=True,
                              scan_progress="Scanning", scan_hits=())
        self._publish(generation)
        try:
            for index in range(count):
                if self._scan_cancel.is_set() or not self._current(generation):
                    break
                frequency = low + index * step
                strength = self._radio.scan_tune(frequency)
                if strength is not None:
                    samples.append((frequency, strength))
                if index % 10 == 0:
                    self._state = replace(self._state,
                        scan_progress=f"Scanning {index + 1}/{count}")
                    self._publish(generation)
                sleep(.06)
            if samples:
                floor = min(v for _, v in samples)
                threshold = floor + 6.0
                hits = tuple(f for i, (f, v) in enumerate(samples)
                             if v >= threshold
                             and (i == 0 or v >= samples[i-1][1])
                             and (i == len(samples)-1 or v >= samples[i+1][1]))
                message = f"Found {len(hits)} signals"
            else:
                hits = ()
                message = "Signal strength unavailable"
            self._state = replace(self._state, scan_hits=hits, scan_progress=message)
        finally:
            self._radio.scan_tune(original)
            self._state = replace(self._state, station=self._radio.state,
                                  scanning=False)
            self._publish(generation)

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
        self._scan_cancel.set()
        with self._lock:
            if not self._active:
                return
            self._active = False
            self._generation += 1
            self._view = None
        # Detach before Tk destroys the host. A launch already in progress must
        # finish first; generation retirement prevents any later reattachment.
        if self._spectrum_source is not None:
            self._spectrum_source.close()
        with self._native_lock:
            self._cleanup_native()

    def _release_owned_receiver(self) -> None:
        if not self._owns_receiver:
            return
        self._owns_receiver = False

        def stop_owned() -> None:
            try:
                with urllib.request.urlopen(
                    urllib.request.Request(
                        "http://127.0.0.1:5570/v1/receiver/stop",
                        data=b"", method="POST"),
                    timeout=5.0,
                ):
                    pass
            except (OSError, urllib.error.HTTPError):
                pass

        # Never block the Tk shutdown path on USB acquisition teardown.
        Thread(target=stop_owned, name="orc-sdrforge-stop", daemon=False).start()

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
        try:
            self._release_owned_receiver()
            self.deactivate()
        finally:
            self._on_close()
