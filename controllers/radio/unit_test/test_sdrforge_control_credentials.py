# SPDX-License-Identifier: MIT
"""Scope the managed credential to local SDRForge mutations."""

from urllib.request import Request

import pytest

from protocols.sdrforge_control import authorize_local_sdrforge_request


@pytest.mark.parametrize(
    ("url", "method", "expected"),
    [
        ("http://127.0.0.1:5570/v1/receiver/start", "POST", "test-token"),
        ("http://127.0.0.1:5570/v1/receiver", "GET", None),
        ("http://example.org:5570/v1/receiver/start", "POST", None),
    ],
)
def test_local_credential_scope(monkeypatch, url, method, expected):
    monkeypatch.setenv("SDRFORGE_ACQUISITION_TOKEN", "test-token")
    request = authorize_local_sdrforge_request(Request(url, method=method))
    assert request.get_header("X-sdrforge-acquisition-token") == expected
    assert "X-sdrforge-acquisition-token" not in request.headers
