from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from protocols.oauth import (
    OAuthTokens,
    OAuthTokenStoreIf,
)


DEFAULT_TOKEN_PATH = (
    Path.home()
    / ".config"
    / "spotify"
    / "tokens.json"
)


class SpotifyTokenStore(OAuthTokenStoreIf):
    """
    Stores Spotify OAuth tokens in a JSON file.
    """

    def __init__(
        self,
        path: Path = DEFAULT_TOKEN_PATH,
    ) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Return the token-store file path.

        @return Absolute or configured path used for token persistence.
        """
        return self._path

    def load(self) -> OAuthTokens | None:
        if not self._path.exists():
            return None

        with self._path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        refresh_token_value = data.get(
            "refresh_token"
        )

        scope_value = data.get("scope")

        return OAuthTokens(
            access_token=str(data["access_token"]),
            refresh_token=(
                str(refresh_token_value)
                if refresh_token_value is not None
                else None
            ),
            expires_at=float(data["expires_at"]),
            token_type=str(
                data.get("token_type", "Bearer")
            ),
            scope=(
                str(scope_value)
                if scope_value is not None
                else None
            ),
        )

    def save(self, tokens: OAuthTokens) -> None:
        self._path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._path.parent.chmod(0o700)

        data = {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "expires_at": tokens.expires_at,
            "token_type": tokens.token_type,
            "scope": tokens.scope,
        }

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
            if (
                temporary_path is not None
                and temporary_path.exists()
            ):
                temporary_path.unlink()

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
