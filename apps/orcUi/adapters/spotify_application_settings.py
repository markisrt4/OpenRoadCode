# SPDX-License-Identifier: MIT
"""User-owned Spotify application settings for the ORC desktop shell."""

from pathlib import Path
from collections.abc import Mapping
import os
import re

from common.xdg_paths import openroadcode_config_dir
from protocols.auth.secure_json_store import SecureJsonStore
from protocols.spotify import (
    SPOTIFY_CLIENT_ID_SECRET_NAME,
    SPOTIFY_REDIRECT_URI_SECRET_NAME,
)
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager
from security.secret_manager_if import SecretManagerIf


DEFAULT_SPOTIFY_SETTINGS_PATH = openroadcode_config_dir("spotify", "application.json")
_CLIENT_ID_PATTERN = re.compile(r"[A-Za-z0-9]{32}")


class SpotifyApplicationSettingsStore:
    """Persist the public PKCE client identifier outside system secrets."""

    def __init__(self, path: str | Path = DEFAULT_SPOTIFY_SETTINGS_PATH) -> None:
        self._store = SecureJsonStore(Path(path).expanduser())

    @property
    def path(self) -> Path:
        return self._store.path

    def load_client_id(self) -> str | None:
        try:
            data = self._store.load()
        except (OSError, TypeError, ValueError):
            return None
        if data is None:
            return None
        value = data.get("client_id")
        if not isinstance(value, str):
            return None
        return self._normalize_client_id(value)

    def save_client_id(self, client_id: str) -> None:
        normalized = self._normalize_client_id(client_id)
        if normalized is None:
            raise ValueError(
                "Spotify Client ID must be the 32-character letters-and-numbers "
                "value from the Spotify Developer Dashboard"
            )
        self._store.save({"client_id": normalized})

    def resolve_client_id(
        self,
        *,
        environment_value: str | None,
        system_value: str | None,
    ) -> str | None:
        """Resolve environment, user, then system configuration precedence."""
        return (
            self._normalize_client_id(environment_value)
            or self.load_client_id()
            or self._normalize_client_id(system_value)
        )

    @staticmethod
    def _normalize_client_id(value: str | None) -> str | None:
        normalized = (value or "").strip()
        return normalized if _CLIENT_ID_PATTERN.fullmatch(normalized) else None


def create_spotify_secret_manager(
    store: SpotifyApplicationSettingsStore | None = None,
    *,
    system_secrets: SecretManagerIf | None = None,
    environment: Mapping[str, str] | None = None,
) -> SecretManagerIf:
    """Build resolved Spotify configuration without granting UI access to `/etc`."""
    resolved_store = store or SpotifyApplicationSettingsStore()
    resolved_system = system_secrets or EnvironmentVariableSecretManager()
    resolved_environment = os.environ if environment is None else environment
    client_id = resolved_store.resolve_client_id(
        environment_value=resolved_environment.get(SPOTIFY_CLIENT_ID_SECRET_NAME),
        system_value=resolved_system.get_secret(SPOTIFY_CLIENT_ID_SECRET_NAME),
    )
    redirect_uri = (
        resolved_environment.get(SPOTIFY_REDIRECT_URI_SECRET_NAME, "").strip()
        or resolved_system.get_secret(SPOTIFY_REDIRECT_URI_SECRET_NAME)
    )
    values = {}
    if client_id:
        values[SPOTIFY_CLIENT_ID_SECRET_NAME] = client_id
    if redirect_uri:
        values[SPOTIFY_REDIRECT_URI_SECRET_NAME] = redirect_uri
    return EnvironmentVariableSecretManager(environment=values)
