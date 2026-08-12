# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Filesystem-backed implementation of persistent byte caching."""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
from pathlib import Path


class PersistentCache:
    """Persist opaque bytes using hashed filenames and atomic replacement."""

    def __init__(
        self,
        directory: str | Path,
        *,
        suffix: str = ".cache",
    ) -> None:
        if not suffix.startswith(".") or "/" in suffix:
            raise ValueError("suffix must be a filename extension")
        self.directory = Path(directory).expanduser()
        self.suffix = suffix
        self._lock = threading.RLock()

    def get(self, key: str) -> bytes | None:
        """Return cached bytes or None when the key is absent."""
        path = self._path(key)
        with self._lock:
            try:
                return path.read_bytes()
            except (FileNotFoundError, OSError):
                return None

    def put(self, key: str, data: bytes) -> None:
        """Atomically store bytes under a logical key."""
        if not isinstance(data, bytes):
            raise TypeError("data must be bytes")
        path = self._path(key)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.",
                dir=path.parent,
            )
            try:
                with os.fdopen(descriptor, "wb") as output:
                    output.write(data)
                os.replace(temporary_name, path)
            finally:
                try:
                    Path(temporary_name).unlink()
                except FileNotFoundError:
                    pass

    def remove(self, key: str) -> bool:
        """Remove a key if present."""
        path = self._path(key)
        with self._lock:
            try:
                path.unlink()
            except FileNotFoundError:
                return False
        return True

    def _path(self, key: str) -> Path:
        normalized = key.strip()
        if not normalized:
            raise ValueError("key cannot be empty")
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}{self.suffix}"
