# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Contract for persistent byte-oriented cache storage."""

from typing import Protocol


class PersistentCacheIf(Protocol):
    """Store opaque bytes under stable logical keys."""

    def get(self, key: str) -> bytes | None:
        """Return cached bytes or None when the key is absent.

        @param key Non-empty logical cache key.
        @return Stored bytes or None.
        """
        ...

    def put(self, key: str, data: bytes) -> None:
        """Atomically store bytes under a logical key.

        @param key Non-empty logical cache key.
        @param data Bytes to persist.
        """
        ...

    def remove(self, key: str) -> bool:
        """Remove a key if present.

        @param key Non-empty logical cache key.
        @retval True A stored entry was removed.
        @retval False The key was absent.
        """
        ...
