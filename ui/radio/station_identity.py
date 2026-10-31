# SPDX-License-Identifier: MIT
"""Shared Detroit FM identities for tuner and MusicForge chart labels.

Unknown stations retain their original labels; never infer a frequency.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StationIdentity:
    call_sign: str
    frequency_mhz: float

    @property
    def label(self) -> str:
        return f"{self.call_sign} · {self.frequency_mhz:.1f} FM"


DETROIT_FM_STATIONS: tuple[StationIdentity, ...] = (
    StationIdentity("WCSX", 94.7),
    StationIdentity("WRIF", 101.1),
    StationIdentity("WOMC", 104.3),
    StationIdentity("WJLB", 97.9),
    StationIdentity("WNIC", 100.3),
    StationIdentity("WDMK", 105.9),
    StationIdentity("WYCD", 99.5),
)

_BY_CALL = {item.call_sign: item for item in DETROIT_FM_STATIONS}
_BY_FREQUENCY = {round(item.frequency_mhz, 1): item for item in DETROIT_FM_STATIONS}


def station_label(call_sign: str) -> str:
    item = _BY_CALL.get(call_sign.upper())
    return item.label if item else call_sign


def preset_label(label: str, frequency_hz: int) -> str:
    item = _BY_FREQUENCY.get(round(frequency_hz / 1_000_000, 1))
    return item.label if item else label
