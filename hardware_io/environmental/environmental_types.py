"""Common types used by environmental hardware devices."""

from __future__ import annotations

from enum import StrEnum


class PressureUnit(StrEnum):
    """Units supported for atmospheric pressure values."""

    PASCAL = "Pa"
    HECTOPASCAL = "hPa"
