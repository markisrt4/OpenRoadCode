# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bandwidth-aware scheduling for request-limited OBD-II links."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
from enum import Enum

from protocols.obd2.obd_pid_decoder import ObdPidDecoder


class Obd2PollingProfile(str, Enum):
    NORMAL = "normal"
    PERFORMANCE = "performance"
    ENGINE = "engine"
    ECU = "ecu"
    TRIP = "trip"


PROFILE_SCHEDULES: dict[Obd2PollingProfile, tuple[str, ...]] = {
    Obd2PollingProfile.NORMAL: (
        "rpm", "map", "rpm", "standard", "rpm", "map",
        "standard", "rpm", "slow", "map", "standard", "rpm",
    ),
    Obd2PollingProfile.PERFORMANCE: (
        "rpm", "map", "rpm", "map", "rpm", "performance",
        "rpm", "map", "rpm", "performance", "map", "standard",
    ),
    Obd2PollingProfile.ENGINE: (
        "rpm", "map", "engine", "rpm", "engine", "map",
        "engine", "rpm", "standard", "engine", "map", "slow",
    ),
    Obd2PollingProfile.ECU: (
        "rpm", "ecu", "map", "ecu", "rpm", "ecu",
        "standard", "ecu", "map", "ecu", "rpm", "slow",
    ),
    Obd2PollingProfile.TRIP: (
        "rpm", "map", "trip", "rpm", "trip", "map",
        "trip", "rpm", "standard", "trip", "map", "slow",
    ),
}


class Obd2PollScheduler:
    """Choose one supported PID per physical OBD transaction opportunity."""

    def __init__(
        self,
        *,
        rpm: ObdPidDecoder,
        manifold_pressure: ObdPidDecoder,
        standard: Sequence[ObdPidDecoder],
        slow: Sequence[ObdPidDecoder],
        performance: Sequence[ObdPidDecoder] = (),
        engine: Sequence[ObdPidDecoder] = (),
        ecu: Sequence[ObdPidDecoder] = (),
        trip: Sequence[ObdPidDecoder] = (),
        supported_pids: set[int] | None,
        profile: Obd2PollingProfile = Obd2PollingProfile.NORMAL,
    ) -> None:
        self._rpm = rpm
        self._map = manifold_pressure
        self._supported_pids = supported_pids
        self._queues = {
            "standard": deque(self._supported(standard)),
            "slow": deque(self._supported(slow)),
            "performance": deque(self._supported(performance)),
            "engine": deque(self._supported(engine)),
            "ecu": deque(self._supported(ecu)),
            "trip": deque(self._supported(trip)),
        }
        self._profile = profile
        self._index = 0

    @property
    def profile(self) -> Obd2PollingProfile:
        return self._profile

    def set_profile(self, profile: Obd2PollingProfile) -> None:
        """Change weighting without discarding per-group round-robin position."""
        if profile == self._profile:
            return
        self._profile = profile
        self._index = 0

    def next_decoder(self) -> ObdPidDecoder | None:
        """Return the next supported decoder for the active profile."""
        schedule = PROFILE_SCHEDULES[self._profile]
        for _ in range(len(schedule)):
            token = schedule[self._index]
            self._index = (self._index + 1) % len(schedule)

            if token == "rpm":
                decoder = self._rpm
            elif token == "map":
                decoder = self._map
            else:
                decoder = self._rotate(self._queues[token])

            if decoder is not None and self._is_supported(decoder):
                return decoder
        return None

    def _supported(
        self,
        decoders: Iterable[ObdPidDecoder],
    ) -> tuple[ObdPidDecoder, ...]:
        return tuple(decoder for decoder in decoders if self._is_supported(decoder))

    def _is_supported(self, decoder: ObdPidDecoder) -> bool:
        return self._supported_pids is None or decoder.pid in self._supported_pids

    @staticmethod
    def _rotate(queue: deque[ObdPidDecoder]) -> ObdPidDecoder | None:
        if not queue:
            return None
        decoder = queue[0]
        queue.rotate(-1)
        return decoder
