# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Cached real-audio presentation and Home visibility contract."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class HomeSpectrumState:
    """Fresh, normalized 0..1 bands; inactive snapshots contain no bands."""

    bands: tuple[float, ...] = ()
    active: bool = False


class HomeSpectrumFeedIf(Protocol):
    """Keep user-started capture while Home is visible, without starting it."""

    def attach_home(self) -> None:
        """Register a visible Home consumer without starting capture."""
        ...

    def detach_home(self) -> None:
        """Release a Home consumer; stop capture when neither view needs it."""
        ...

    def read_spectrum(self) -> HomeSpectrumState:
        """Read cached audio without backend or transport work.

        @return Fresh real-audio bands, or an inactive snapshot.
        """
        ...
