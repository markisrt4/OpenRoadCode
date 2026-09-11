# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Bandwidth-aware scheduling for serial OBD-II request streams."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence

from protocols.obd2.obd_pid_decoder import ObdPidDecoder


DEFAULT_WEIGHTED_SCHEDULE = (
    "rpm",
    "map",
    "rpm",
    "standard",
    "rpm",
    "map",
    "standard",
    "rpm",
    "slow",
    "map",
    "standard",
    "rpm",
)


class Obd2PollScheduler:
    """Choose one supported PID per physical OBD transaction opportunity."""

    def __init__(
        self,
        *,
        rpm: ObdPidDecoder,
        manifold_pressure: ObdPidDecoder,
        standard: Sequence[ObdPidDecoder],
        slow: Sequence[ObdPidDecoder],
        supported_pids: set[int] | None,
        schedule: Sequence[str] = DEFAULT_WEIGHTED_SCHEDULE,
    ) -> None:
        if not schedule:
            raise ValueError("schedule must not be empty")
        self._schedule = tuple(schedule)
        self._index = 0
        self._rpm = rpm
        self._map = manifold_pressure
        self._supported_pids = supported_pids
        self._standard = deque(self._supported(standard))
        self._slow = deque(self._supported(slow))

    def next_decoder(self) -> ObdPidDecoder | None:
        """Return the next decoder without scheduling unsupported PIDs."""
        for _ in range(len(self._schedule)):
            token = self._schedule[self._index]
            self._index = (self._index + 1) % len(self._schedule)

            if token == "rpm":
                decoder = self._rpm
            elif token == "map":
                decoder = self._map
            elif token == "standard":
                decoder = self._rotate(self._standard)
            elif token == "slow":
                decoder = self._rotate(self._slow)
            else:
                raise ValueError(f"unknown OBD poll schedule token: {token}")

            if decoder is not None and self._is_supported(decoder):
                return decoder
        return None

    def _supported(
        self,
        decoders: Iterable[ObdPidDecoder],
    ) -> tuple[ObdPidDecoder, ...]:
        return tuple(decoder for decoder in decoders if self._is_supported(decoder))

    def _is_supported(self, decoder: ObdPidDecoder) -> bool:
        return (
            self._supported_pids is None
            or decoder.pid in self._supported_pids
        )

    @staticmethod
    def _rotate(
        queue: deque[ObdPidDecoder],
    ) -> ObdPidDecoder | None:
        if not queue:
            return None
        decoder = queue[0]
        queue.rotate(-1)
        return decoder
