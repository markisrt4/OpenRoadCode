# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Compatibility import for :class:`enum.StrEnum`."""

try:
    from enum import StrEnum
except ImportError:  # Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport the string behavior needed by the project's enums."""

        def __str__(self) -> str:
            return self.value


__all__ = ["StrEnum"]
