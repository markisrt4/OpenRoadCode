# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Audio sample capture contract for shared analysis pipelines."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence

AudioSamplesCallback = Callable[[Sequence[float], int], None]


class AudioCaptureIf(ABC):
    """Produce normalized mono PCM blocks independent of capture backend."""

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Return whether this capture backend is currently running.

        @return True while capture is active.
        """
        raise NotImplementedError

    @abstractmethod
    def start(self, callback: AudioSamplesCallback) -> None:
        """Begin capture and invoke callback(samples, sample_rate_hz).

        @param callback Consumer for normalized samples and their sample rate.
        """
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """Stop capture and release backend resources."""
        raise NotImplementedError
