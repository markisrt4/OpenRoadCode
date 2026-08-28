# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Common types used by environmental hardware devices."""

from __future__ import annotations

from common.str_enum import StrEnum


class PressureUnit(StrEnum):
    """Units supported for atmospheric pressure values."""

    PASCAL = "Pa"
    HECTOPASCAL = "hPa"
