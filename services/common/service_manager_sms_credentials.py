# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Private local storage for the Android SMS gateway bearer credential.

Provisioning must be separately authorized by the HTTP layer. This module
never provides an unauthenticated provisioning endpoint.
"""

from __future__ import annotations

import os
from pathlib import Path
import secrets
import tempfile

from common.xdg_paths import xdg_config_home


def default_path() -> Path:
    return xdg_config_home() / "openroadcode" / "service-manager" / "android-sms-token"


def load_token(path: Path | None = None) -> str | None:
    target = path or default_path()
    try:
        if target.is_symlink():
            return None
        mode = target.stat().st_mode & 0o777
        if mode & 0o077:
            return None
        value = target.read_text(encoding="utf-8").strip()
        return value if value else None
    except (OSError, UnicodeError):
        return None


def save_token(token: str, path: Path | None = None) -> None:
    """Atomically replace a credential without writing it to logs."""
    if not isinstance(token, str) or not 32 <= len(token) <= 256:
        raise ValueError("invalid SMS credential")
    if any(character.isspace() for character in token):
        raise ValueError("invalid SMS credential")
    target = path or default_path()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)
    if target.is_symlink():
        raise ValueError("refusing credential symlink")
    descriptor, name = tempfile.mkstemp(prefix=".sms-", dir=target.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(token + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def delete_token(path: Path | None = None) -> None:
    target = path or default_path()
    if target.is_symlink():
        raise ValueError("refusing credential symlink")
    target.unlink(missing_ok=True)
