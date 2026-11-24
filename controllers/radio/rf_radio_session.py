# SPDX-License-Identifier: MIT
"""Receiver orchestration; workers never touch a GUI or its native host widget."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from threading import Event, Lock, RLock, Thread
from time import monotonic, sleep
import json
import urllib.request
import urllib.error

from controllers.radio.radio_profile_controller import RadioProfileController
from typing import Protocol
from ui.notification_if import Notification, NotificationSeverity, NotificationSinkIf
from ui.radio.radio_profile_state import RadioProfileState
from ui.radio.sdrforge_spectrum_if import SpectrumSourceIf, SpectrumPresentationIf
from ui.radio.rf_radio_if import (
    AircraftPresentation, RadioAction, RadioApplication, RadioHost, RadioNativeSurface,
    RadioRequest, RadioTelemetry, RfProfile, RfRadioState, RfRadioUi,
)


class RadioDisplayControlIf(Protocol):
    """Presentation controls shared by native and legacy RF implementations."""

    def set_theme(self, theme: str) -> object: ...
    def toggle_waterfall(self) -> object: ...
    def toggle_bandplan(self) -> object: ...
    def toggle_fft_hold(self) -> object: ...
    def auto_range(self) -> object: ...
    def waterfall_visible(self) -> bool: ...
    def bandplan_visible(self) -> bool: ...
    def fft_hold_enabled(self) -> bool: ...
    def themes(self) -> tuple[str, ...]: ...


class ReceiverSession:
    """Use a composition-owned serial executor for shared receiver/native operations.

    Retirement is immediate. Cleanup remains on the same serial executor as launch,
    so an in-flight embed finishes and detaches before another session can launch.
    """

    def __init__(self, radio: RadioProfileController, control: RadioDisplayControlIf,
                 application: RadioApplication,
                 aircraft: AircraftPresentation, surface: RadioNativeSurface, *,
                 display: str, run_work: Callable[[Callable[[], None]], None],
                 run_ui: Callable[[Callable[[], None]], None],
                 on_close: Callable[[], None] = lambda: None,
                 spectrum_source: SpectrumSourceIf | None = None,
                 notification_sink: NotificationSinkIf | None = None) -> None:
        self._spectrum_source = spectrum_source
        self._radio = radio
        self._control = control
        self._application = application
        self._aircraft = aircraft
        self._surface = surface
        self._display = display
        self._run_work = run_work
        self._run_ui = run_ui
        self._on_close = on_close
        self._notification_sink = notification_sink
        self._lock = Lock()
        self._native_lock = RLock()
        self._generation = 0
        self._closed = False
        self._active = True
        self._refresh_pending = False
        self._scan_cancel = Event()
        self._owns_receiver = False
        self._rest_receiver_running: bool | None = None
        self._view: RfRadioUi | None = None
        self._host: RadioHost | None = None
        self._native_view = "none"
        self._next_catalog_refresh = 0.0
        self._state = RfRadioState(
            radio.state, self._profiles(), waterfall=True,
            presets_writable=radio.catalog.presets_writable,
        )

    def _set_station(self, station: RadioProfileState) -> None:
        """Invalidate telemetry when rigctl or a local request changes station."""
        if (station.frequency_hz != self._state.station.frequency_hz
                or station.mode_name != self._state.station.mode_name
                or station.profile_key != self._state.station.profile_key):
            self._state = replace(self._state, station=station, telemetry=RadioTelemetry())
        else:
            self._state = replace(self._state, station=station)

    def _profiles(self) -> tuple[RfProfile, ...]:
        return tuple(RfProfile(p.key, p.label, p.group, p.presets) for p in self._radio.catalog.profiles)

    def bind(self, view: RfRadioUi) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Receiver session is closed")
            self._view = view
        if self._spectrum_source is not None:
            self._spectrum_source.start()
        view.set_radio_state(replace(self._state, tuning_range=self._radio.scan_range))

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
            # A delayed packet from a previous acquisition must not resurrect
            # RDS or observed mode after REST confirms the receiver stopped.
            if self._rest_receiver_running is False:
                receiver = replace(receiver, station_name="", radio_text="",
                                   rds="", mode=None, bandwidth_hz=None,
                                   stereo_locked=None)
            # Spectrum telemetry may omit RDS fields between decoder updates.
            # Preserve the last decoded text only while tuned to the same station.
            previous = self._state.telemetry
            if (self._rest_receiver_running is not False
                    and receiver.receiver_running is not False
                    and receiver.frequency_hz == previous.frequency_hz
                    and receiver.frequency_hz == self._state.station.frequency_hz
                    and not (receiver.radio_text or receiver.station_name or receiver.rds)):
                receiver = replace(receiver, radio_text=previous.radio_text,
                                   station_name=previous.station_name, rds=previous.rds)
            elif (self._rest_receiver_running is False
                  or receiver.receiver_running is False
                  or receiver.frequency_hz != self._state.station.frequency_hz):
                # A stopped or previously tuned receiver must not advertise
                # station identity from an earlier listening session.
                receiver = replace(receiver, radio_text="", station_name="", rds="")
            # Preserve the requested profile mode. Replacing it with ZMQ's
            # observed mode would hide mismatches and corrupt profile state.
            station = self._state.station
            if receiver.frequency_hz != station.frequency_hz:
                # An old receiver message must not override a newly tuned station.
                receiver = replace(receiver, mode=None, bandwidth_hz=None,
                                   receiver_running=None)
            # REST owns acquisition state once a successful status read arrives.
            # ZMQ can report an older start/stop event after that REST snapshot.
            running = (self._rest_receiver_running
                       if self._rest_receiver_running is not None
                       else (self._state.receiver_running
                             if receiver.receiver_running is None
                             else receiver.receiver_running))
            self._state = replace(self._state, telemetry=receiver,
                                  receiver_running=running)
            view.set_radio_state(self._state)
        snapshot = self._spectrum_source.latest_spectrum()
        if (snapshot is not None
                and self._rest_receiver_running is not False
                and self._state.receiver_running
                and isinstance(view, SpectrumPresentationIf)):
            # FFT geometry describes acquisition, not the listening channel.
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
                if self._notification_sink is not None and request.action in (
                    RadioAction.LAUNCH, RadioAction.ADSB,
                ):
                    adsb = request.action is RadioAction.ADSB
                    notification = Notification(
                        code="adsb.launch_failed" if adsb else "radio.launch_failed",
                        title="ADS-B Map Unavailable" if adsb else "Radio Launch Failed",
                        message=message,
                        severity=NotificationSeverity.ERROR,
                        source="adsb" if adsb else "radio",
                    )
                    self._notification_sink.publish(notification)
                    self._state = replace(self._state, loading=False, error="")
                else:
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
        self._state = replace(
            self._state, presets_writable=self._radio.catalog.presets_writable,
        )
        state = replace(self._state, tuning_range=self._radio.scan_range)
        def deliver() -> None:
            if self._current(generation) and self._view is not None:
                self._view.set_radio_state(state)
        self._run_ui(deliver)

    def _launch(self, request: RadioRequest, generation: int) -> None:
        if request.action is RadioAction.LAUNCH:
            # The native Tk receiver already exists; never launch or embed SDR++.
            # ADS-B still uses the existing native-window lifecycle.
            with self._native_lock:
                if not self._current(generation):
                    return
                if self._native_view == "adsb":
                    self._cleanup_native()
                self._native_view = "none"
            self._state = replace(self._state, view="none", loading=False, error="")
            return
        host = self._host
        if host is None:
            raise ValueError("A native host is required")
        with self._native_lock:
            if not self._current(generation):
                return
            self._cleanup_native()
        self._state = replace(self._state, loading=True, error="")
        self._publish(generation)
        self._application.relinquish_for_adsb()
        with self._native_lock:
            if not self._current(generation):
                return
            self._aircraft.assert_available()
            self._aircraft.set_preferred_color_scheme(request.color_scheme)
            self._aircraft.configure_browser_window(position=(host.x, host.y), size=(host.width, host.height))
            self._aircraft.launch(self._display)
            self._native_view = "adsb"
        with self._native_lock:
            if not self._current(generation):
                self._cleanup_native()
                return
            self._surface.embed(0, host.window_id, host.width, host.height,
                                window_class="OpenRoadCodeADSB", relax_size_hints=False,
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
        if action is RadioAction.PAN_ACQUISITION:
            if request.frequency_hz is None:
                raise ValueError("pan requires an acquisition center")
            with urllib.request.urlopen(
                urllib.request.Request(
                    "http://127.0.0.1:5570/v1/receiver/pan",
                    data=('{"center_hz": %d}' % request.frequency_hz).encode(),
                    headers={"Content-Type": "application/json"}, method="POST",
                ), timeout=6.0,
            ) as response:
                if response.status != 202:
                    raise RuntimeError("SDRForge acquisition pan failed")
            return
        if action is RadioAction.RECENTER:
            with urllib.request.urlopen(
                urllib.request.Request(
                    "http://127.0.0.1:5570/v1/receiver/recenter",
                    data=b"", method="POST",
                ), timeout=6.0,
            ) as response:
                if response.status != 202:
                    raise RuntimeError("SDRForge acquisition recenter failed")
            self._state = replace(self._state, error="")
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
            # SDRForge is shared: leaving this UI must not stop acquisition.
            self._owns_receiver = False
            # HTTP 202 means startup was accepted, not that acquisition is running.
            # Periodic REST refresh will report the actual receiver state.
            if action is RadioAction.STOP_RECEIVER:
                self._rest_receiver_running = False
            else:
                # A 202 Accepted response does not establish running state.
                self._rest_receiver_running = None
            # Neither a completed stop nor an accepted restart may carry the
            # previous acquisition's station identity into the next session.
            self._state = replace(self._state,
                                  receiver_running=False,
                                  receiver_starting=action is RadioAction.START_RECEIVER,
                                  telemetry=RadioTelemetry(),
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
            now = monotonic()
            if now >= self._next_catalog_refresh:
                self._radio.catalog.reload()
                self._next_catalog_refresh = monotonic() + 5.0
                self._state = replace(self._state, profiles=self._profiles())
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
                    startup_error = status.get("startup_error")
                    running = bool(status.get("running", False))
                    starting = bool(status.get("starting", False)) and not running
                    self._rest_receiver_running = running
                    if not self._rest_receiver_running:
                        self._state = replace(self._state, telemetry=RadioTelemetry())
                    self._state = replace(
                        self._state, receiver_running=running,
                        receiver_starting=starting,
                        playing=not bool(audio_status.get("muted", False)),
                        error=(f"SDRForge startup failed: {startup_error}" if startup_error else
                               "" if (self._state.error.startswith("SDRForge service unavailable:")
                                      or self._state.error.startswith("SDRForge startup failed:"))
                               else self._state.error),
                    )
                except (OSError, ValueError, RuntimeError) as exc:
                    # REST is authoritative for acquisition. A disconnected
                    # service must not leave the last receiver marked running.
                    self._rest_receiver_running = False
                    self._state = replace(
                        self._state, receiver_running=False,
                        receiver_starting=False, telemetry=RadioTelemetry(),
                        error=f"SDRForge service unavailable: {exc}",
                    )
                try:
                    # A successful rigctl frequency read must not erase a
                    # receiver startup failure reported by REST.
                    self._set_station(self._radio.refresh())
                except (OSError, RuntimeError, ValueError):
                    # Preserve the last valid station during transient rigctl failures.
                    # REST remains authoritative for acquisition state.
                    pass
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
            frequency_hz = (request.frequency_hz if request.frequency_hz is not None
                            else self._radio.state.frequency_hz)
            if request.frequency_hz is not None and frequency_hz not in self._state.scan_hits:
                raise ValueError("Selected frequency is not in the latest scan results")
            if request.key != self._radio.active_profile_key:
                raise ValueError("Cannot save a preset to an inactive radio profile")
            existing = self._radio.catalog.profile(request.key).presets
            if any(p.frequency_hz == frequency_hz for p in existing):
                raise ValueError("A preset already exists at this frequency")
            self._radio.catalog.add_user_preset(
                request.key, label=request.label, frequency_hz=frequency_hz,
            )
        elif action is RadioAction.THEME:
            self._control.set_theme(request.key)
        else:
            operations: dict[RadioAction, Callable[[], object]] = {
                RadioAction.PREVIOUS: self._radio.previous_preset,
                RadioAction.NEXT: self._radio.next_preset,
                RadioAction.TUNE_DOWN: self._radio.tune_down,
                RadioAction.TUNE_UP: self._radio.tune_up,
                RadioAction.WATERFALL: self._toggle_waterfall,
                RadioAction.BANDPLAN: self._control.toggle_bandplan,
                RadioAction.FFT_HOLD: self._control.toggle_fft_hold,
                RadioAction.AUTO_RANGE: self._control.auto_range,
            }
            operations[action]()
        self._set_station(self._radio.state)
        self._state = replace(self._state, profiles=self._profiles(), error="")
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

    def _toggle_waterfall(self) -> None:
        if self._spectrum_source is not None:
            self._state = replace(self._state, waterfall=not self._state.waterfall)
        else:
            self._control.toggle_waterfall()

    def _read_controls(self) -> None:
        try:
            self._state = replace(self._state, waterfall=(self._state.waterfall if self._spectrum_source is not None
                                             else self._control.waterfall_visible()),
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
