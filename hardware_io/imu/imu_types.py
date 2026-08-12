# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Common inertial measurement unit data types."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Vector3:
    """Represent a three-dimensional vector."""

    x: float
    y: float
    z: float
