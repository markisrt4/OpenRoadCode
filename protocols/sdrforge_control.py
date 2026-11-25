# SPDX-License-Identifier: MIT
"""Credentials for mutations on the local SDRForge control service."""

from os import environ
from urllib.request import Request


def authorize_local_sdrforge_request(request: Request) -> Request:
    """Attach the configured credential to local POST requests only."""
    token = environ.get("SDRFORGE_ACQUISITION_TOKEN")
    if (
        token
        and request.get_method() == "POST"
        and request.type == "http"
        and request.host in {"localhost:5570", "127.0.0.1:5570", "[::1]:5570"}
    ):
        request.add_unredirected_header("X-SDRForge-Acquisition-Token", token)
    return request
