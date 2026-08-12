# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any

from protocols.spotify.spotify_auth import (
    SpotifyAuth,
)


SPOTIFY_API_BASE_URL = (
    "https://api.spotify.com/v1"
)


class SpotifyWebApiError(RuntimeError):
    """
    Raised when a Spotify Web API request fails.
    """

    def __init__(
        self,
        status_code: int,
        response_body: str,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body

        super().__init__(
            f"Spotify HTTP {status_code}: "
            f"{response_body}"
        )


class SpotifyWebApiClient:
    """
    Client for sending authenticated Spotify Web API requests.
    """

    def __init__(
        self,
        auth: SpotifyAuth,
        *,
        base_url: str = SPOTIFY_API_BASE_URL,
        timeout_seconds: float = 10.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url cannot be empty")

        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Send a Spotify request and decode a JSON response.
        """
        request = self._build_request(
            method,
            path,
            body=body,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ) as response:
                if response.status == 204:
                    return None

                response_body = (
                    response.read().decode("utf-8")
                )

                if not response_body:
                    return None

                parsed = json.loads(response_body)

                if not isinstance(parsed, dict):
                    raise RuntimeError(
                        "Spotify response was not a JSON object"
                    )

                return parsed

        except urllib.error.HTTPError as exc:
            self._raise_http_error(exc)

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Unable to reach Spotify Web API: {exc}"
            ) from exc

        return None

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None = None,
    ) -> None:
        """
        Send a Spotify request when no response body is expected.
        """
        request = self._build_request(
            method,
            path,
            body=body,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._timeout_seconds,
            ):
                return

        except urllib.error.HTTPError as exc:
            self._raise_http_error(exc)

        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Unable to reach Spotify Web API: {exc}"
            ) from exc

    def _build_request(
        self,
        method: str,
        path: str,
        *,
        body: Mapping[str, Any] | None,
    ) -> urllib.request.Request:
        normalized_method = method.strip().upper()

        if not normalized_method:
            raise ValueError("method cannot be empty")

        if not path:
            raise ValueError("path cannot be empty")

        normalized_path = (
            path
            if path.startswith("/")
            else f"/{path}"
        )

        token = self._auth.get_access_token()

        data: bytes | None = None

        if body is not None:
            data = json.dumps(body).encode("utf-8")

        return urllib.request.Request(
            f"{self._base_url}{normalized_path}",
            data=data,
            method=normalized_method,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    @staticmethod
    def _raise_http_error(
        error: urllib.error.HTTPError,
    ) -> None:
        response_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise SpotifyWebApiError(
            error.code,
            response_body,
        ) from error
