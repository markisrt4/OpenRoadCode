# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

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
        config_home = Path(
            os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        ).expanduser()
        return config_home / "openroadcode" / "secrets.env"

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
            loaded_environment = self._load_file(resolved_secrets_file)
            loaded_environment.update(os.environ)
            self._environment: Mapping[str, str] = loaded_environment
        else:
            self._environment = environment
        self._prefix = prefix

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
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]
            values[name] = value

        return values
