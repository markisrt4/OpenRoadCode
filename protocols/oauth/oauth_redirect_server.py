# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import urllib.parse
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)
from types import MappingProxyType

from protocols.oauth.oauth_types import OAuthCallbackResult


class OAuthRedirectServer:
    """
    Waits for a single OAuth redirect callback using a local HTTP server.
    """

    def __init__(
        self,
        redirect_uri: str,
        *,
        timeout_seconds: float = 120.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be greater than zero"
            )

        parsed = urllib.parse.urlparse(redirect_uri)

        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                "redirect_uri must use HTTP or HTTPS"
            )

        self._host = parsed.hostname or "127.0.0.1"
        self._port = parsed.port or (
            443 if parsed.scheme == "https" else 80
        )
        self._path = parsed.path or "/"
        self._timeout_seconds = timeout_seconds
        self._callback_parameters: dict[str, str] = {}
        self._server: HTTPServer | None = None

    def start(self) -> None:
        """Bind the callback socket before the authorization browser opens."""
        if self._server is not None:
            return
        self._callback_parameters = {}
        handler = self._create_handler(self._callback_parameters)
        self._server = HTTPServer((self._host, self._port), handler)
        self._server.timeout = self._timeout_seconds

    def close(self) -> None:
        """Close a bound callback socket without waiting for a request."""
        server = self._server
        self._server = None
        if server is not None:
            server.server_close()

    def wait_for_callback(self) -> OAuthCallbackResult:
        """
        Block until a single OAuth callback is received.
        """
        self.start()
        server = self._server
        if server is None:
            raise RuntimeError("OAuth callback server did not start")

        try:
            server.handle_request()
        finally:
            self.close()

        parameters = MappingProxyType(
            dict(self._callback_parameters)
        )

        return OAuthCallbackResult(
            code=self._callback_parameters.get("code"),
            state=self._callback_parameters.get("state"),
            error=self._callback_parameters.get("error"),
            error_description=self._callback_parameters.get(
                "error_description"
            ),
            parameters=parameters,
        )

    def _create_handler(
        self,
        callback_parameters: dict[str, str],
    ) -> type[BaseHTTPRequestHandler]:
        callback_path = self._path

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                parsed = urllib.parse.urlparse(
                    self.path
                )

                if parsed.path != callback_path:
                    self.send_response(404)
                    self.end_headers()
                    return

                query = urllib.parse.parse_qs(
                    parsed.query
                )

                for key, values in query.items():
                    if values:
                        callback_parameters[key] = values[0]

                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )
                self.end_headers()

                self.wfile.write(
                    b"""<!DOCTYPE html>
<html>
<head>
    <title>Authorization Complete</title>
</head>
<body>
    <h2>Authorization Complete</h2>
    <p>You may now close this browser window.</p>
</body>
</html>"""
                )

            def log_message(
                self,
                _format: str,
                *_args: object,
            ) -> None:
                # Suppress default HTTP request logging.
                return

        return CallbackHandler
