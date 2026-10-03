# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from common.xdg_paths import openroadcode_config_dir
from .secret_manager_if import SecretManagerIf

DEFAULT_SECRETS_FILE = Path("/etc/openroadcode/secrets.env")
OPENROADCODE_SECRETS_FILE_ENV = "OPENROADCODE_SECRETS_FILE"


def resolve_default_secrets_file() -> Path:
    """Return the platform-appropriate default OpenRoadCode secrets file."""
    override = os.environ.get(OPENROADCODE_SECRETS_FILE_ENV)
    if override:
        return Path(override).expanduser()

    prefix = os.environ.get("PREFIX", "")
    if prefix.endswith("/com.termux/files/usr"):
        return openroadcode_config_dir("secrets.env")

    return DEFAULT_SECRETS_FILE


class EnvironmentVariableSecretManager(SecretManagerIf):
    """Read secrets from an environment file and process environment.

    Args:
        environment:
            Optional environment mapping. Supplying one is useful for tests.
            When omitted, values are loaded from ``secrets_file`` and then
            overridden by ``os.environ``.

        prefix:
            Optional prefix added before each requested secret name.

        secrets_file:
            Environment-style secrets file used when ``environment`` is
            omitted. When omitted, a platform-appropriate default is resolved
            at runtime.
    """

    def __init__(
        self,
        environment: Mapping[str, str] | None = None,
        *,
        prefix: str = "",
        secrets_file: str | Path | None = None,
    ) -> None:
        if environment is None:
            resolved_secrets_file = (
                resolve_default_secrets_file()
                if secrets_file is None
                else Path(secrets_file)
            )
            self._secrets_file = resolved_secrets_file
            loaded_environment = self._load_file(resolved_secrets_file)
            loaded_environment.update(os.environ)
            self._environment: Mapping[str, str] = loaded_environment
        else:
            self._secrets_file = None
            self._environment = environment
        self._prefix = prefix

    @property
    def secrets_file(self) -> Path | None:
        """Return the backing environment file, when this manager owns one."""
        return getattr(self, "_secrets_file", None)

    def set_secret(self, name: str, value: str) -> None:
        """Persist one secret in the backing environment file.

        Process-environment-only managers are intentionally read-only.
        """
        if not name or not name.strip() or not name.isidentifier():
            raise ValueError("Secret name must be a valid environment variable name")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Secret value cannot be empty")
        path = self.secrets_file
        if path is None:
            raise RuntimeError("Secret manager has no writable backing file")

        path.parent.mkdir(parents=True, exist_ok=True)
        existing = self._load_file(path)
        existing[name] = normalized
        lines = [
            "# OpenRoadCode secrets",
            *[f"{key}={self._quote_value(item)}" for key, item in sorted(existing.items())],
            "",
        ]
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text("\n".join(lines), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(path)

    @staticmethod
    def _quote_value(value: str) -> str:
        if all(character.isalnum() or character in "._-:/@" for character in value):
            return value
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    def get_secret(self, name: str) -> str | None:
        if not name or not name.strip():
            raise ValueError("Secret name cannot be empty")

        environment_name = f"{self._prefix}{name}"
        value = self._environment.get(environment_name)

        if value is None:
            return None

        normalized_value = value.strip()

        if not normalized_value:
            return None

        return normalized_value

    @staticmethod
    def _load_file(path: Path) -> dict[str, str]:
        values: dict[str, str] = {}
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (FileNotFoundError, OSError):
            return values

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].lstrip()
            name, separator, value = line.partition("=")
            name = name.strip()
            if not separator or not name.isidentifier():
                raise ValueError(
                    f"Invalid secret assignment in {path} "
                    f"at line {line_number}"
                )
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                escaped = value[1:-1]
                decoded: list[str] = []
                index = 0
                while index < len(escaped):
                    if escaped[index] == "\\" and index + 1 < len(escaped):
                        following = escaped[index + 1]
                        if following in {'"', "\\"}:
                            decoded.append(following)
                            index += 2
                            continue
                    decoded.append(escaped[index])
                    index += 1
                value = "".join(decoded)
            elif len(value) >= 2 and value[0] == value[-1] == "'":
                value = value[1:-1]
            values[name] = value

        return values
