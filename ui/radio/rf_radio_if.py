# SPDX-License-Identifier: MIT
"""Immutable receiver values and semantic presentation contracts."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Protocol
from ui.radio.radio_profiles import RadioProfilePreset
from ui.radio.radio_profile_state import RadioProfileState


@dataclass(frozen=True)
class RadioHost:
    window_id: int
    parent_id: int
    width: int
    height: int
    x: int = 0
    y: int = 0


@dataclass(frozen=True)
class RadioTelemetry:
    frequency_hz: int | None = None
    signal_db: float | None = None
    snr_db: float | None = None
    rds: str = ""


@dataclass(frozen=True)
class RfProfile:
    key: str
    label: str
    group: str
    presets: tuple[RadioProfilePreset, ...]


@dataclass(frozen=True)
class RfRadioState:
    station: RadioProfileState
    profiles: tuple[RfProfile, ...]
    telemetry: RadioTelemetry = RadioTelemetry()
    view: str = "none"
    loading: bool = False
    error: str = ""
    waterfall: bool = False
    bandplan: bool = False
    fft_hold: bool = False
    themes: tuple[str, ...] = ()


class RadioAction(Enum):
    LAUNCH = "launch"
    ADSB = "adsb"
    PROFILE = "profile"
    PRESET = "preset"
    PREVIOUS = "previous"
    NEXT = "next"
    TUNE_DOWN = "tune_down"
    TUNE_UP = "tune_up"
    ADD_PRESET = "add_preset"
    WATERFALL = "waterfall"
    BANDPLAN = "bandplan"
    FFT_HOLD = "fft_hold"
    AUTO_RANGE = "auto_range"
    THEME = "theme"
    REFRESH = "refresh"
    RESIZE = "resize"


@dataclass(frozen=True)
class RadioRequest:
    action: RadioAction
    key: str = ""
    label: str = ""
    preset: RadioProfilePreset | None = None
    host: RadioHost | None = None
    color_scheme: str = "dark"


class RfRadioUi(Protocol):
    def set_radio_state(self, state: RfRadioState) -> None:
        """Render an immutable receiver snapshot on the frontend thread.
        @param state Immutable receiver presentation values.
        """
        ...


class RfRadioSession(Protocol):
    def bind(self, view: RfRadioUi) -> None:
        """Bind a presentation on its frontend thread; closed sessions reject binding.
        @param view Frontend presentation receiving snapshots.
        """
        ...
    def request(self, request: RadioRequest) -> None:
        """Submit a semantic request; backend work never accesses the widget.
        @param request Semantic receiver action and immutable arguments.
        """
        ...
    def deactivate(self) -> None:
        """Retire requests/results and detach native clients before host destruction.
        """
        ...
    def close(self) -> None:
        """Release ownership once; close is terminal and idempotent.
        """
        ...


class RadioApplication(Protocol):
    def present(self) -> None:
        """Ensure application-owned receiver playback is running.
        """
        ...
    def window_process_id(self, *, timeout_seconds: float) -> int:
        """Find the receiver process for native window discovery.
        @param timeout_seconds Maximum process discovery wait in seconds.
        @return Native window/process identifier.
        """
        ...
    @property
    def fullscreen(self) -> bool:
        """Report whether the receiver uses a standalone fullscreen window.
        @return Current application presentation policy.
        """
        ...
    @property
    def presented(self) -> bool:
        """Report whether the application considers RF presented.
        @return Current application presentation policy.
        """
        ...
    def relinquish_for_adsb(self) -> None:
        """Stop RF ownership so ADS-B can acquire the shared SDR.
        """
        ...


class RadioNativeSurface(Protocol):
    def embed(self, process_id: int, host_window_id: int, width: int, height: int,
              *, window_name: str | None = None, window_class: str | None = None,
              relax_size_hints: bool = False,
              cancelled: Callable[[], bool] | None = None) -> int:
        """Discover and reparent a native client; honor cancellation during discovery.
        @param process_id Native client process identifier.
        @param host_window_id Native host window identifier.
        @param width Host width in native pixels.
        @param height Host height in native pixels.
        @param window_name Optional client title filter.
        @param window_class Optional native class filter.
        @param relax_size_hints Allow resizing beyond client size hints.
        @param cancelled Optional retirement predicate, checked during discovery.
        @return Native window/process identifier.
        """
        ...
    def detach(self, parent_window_id: int) -> None:
        """Reparent a client away from its host before that host is destroyed.
        @param parent_window_id Surviving native parent window identifier.
        """
        ...
    def resize(self, width: int, height: int) -> None:
        """Resize the embedded native client.
        @param width Host width in native pixels.
        @param height Host height in native pixels.
        """
        ...
    def clear(self) -> None:
        """Forget native attachment bookkeeping without constructing resources.
        """
        ...


class AircraftPresentation(Protocol):
    def assert_available(self) -> None:
        """Validate the installed aircraft presentation dependencies.
        """
        ...
    def set_preferred_color_scheme(self, scheme: str) -> None:
        """Configure the preferred aircraft presentation color scheme.
        @param scheme Preferred light or dark color scheme.
        """
        ...
    def configure_browser_window(self, *, position: tuple[int, int], size: tuple[int, int]) -> None:
        """Supply desktop geometry before aircraft browser launch.
        @param position Desktop x/y position in native pixels.
        @param size Width/height in native pixels.
        """
        ...
    def launch(self, display: str) -> None:
        """Launch the aircraft browser on the supplied display.
        @param display Native display address.
        """
        ...
    def stop(self, display: str) -> None:
        """Stop the aircraft browser on the supplied display.
        @param display Native display address.
        """
        ...
