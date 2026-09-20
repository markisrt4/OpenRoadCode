# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Secure atomic JSON persistence for authentication credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any


class SecureJsonStore:
    """Persist JSON objects atomically with private filesystem permissions."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict[str, Any] | None:
        if not self._path.exists():
            return None
        with self._path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("secure JSON record must be an object")
        return data

    def save(self, data: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.parent.chmod(0o700)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                delete=False,
            ) as file:
                temporary_path = Path(file.name)
                os.chmod(file.fileno(), 0o600)
                json.dump(data, file, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            temporary_path.replace(self._path)
            self._path.chmod(0o600)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
