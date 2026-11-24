# SPDX-License-Identifier: MIT
"""Readiness tests: no hardware, sockets, or real sleeps."""

import io
import json
from urllib.error import URLError
from unittest.mock import patch

import pytest

from controllers.radio.sdrforge_readiness import (
    SdrforgeNotReadyError,
    wait_for_sdrforge_ready,
)


def test_waits_for_delayed_service():
    calls = iter(
        [
            URLError("connection refused"),
            io.BytesIO(b'{"status":"starting"}'),
            io.BytesIO(b'{"status":"ok"}'),
        ]
    )

    def fetch(_url, *, timeout):
        result = next(calls)
        if isinstance(result, Exception):
            raise result
        return result

    with patch("controllers.radio.sdrforge_readiness.urlopen", side_effect=fetch) as probe:
        with patch("controllers.radio.sdrforge_readiness.time.sleep"):
            wait_for_sdrforge_ready(timeout=2)
    assert probe.call_count == 3


def test_fails_with_bounded_timeout():
    with patch("controllers.radio.sdrforge_readiness.urlopen", side_effect=URLError("refused")):
        with patch(
            "controllers.radio.sdrforge_readiness.time.monotonic", side_effect=[0.0, 0.01, 0.2]
        ):
            with patch("controllers.radio.sdrforge_readiness.time.sleep"):
                with pytest.raises(SdrforgeNotReadyError, match="not ready"):
                    wait_for_sdrforge_ready(timeout=0.1)


def test_malformed_health_never_counts_as_ready():
    with patch(
        "controllers.radio.sdrforge_readiness.urlopen",
        return_value=io.BytesIO(json.dumps({"status": "starting"}).encode()),
    ):
        with patch(
            "controllers.radio.sdrforge_readiness.time.monotonic", side_effect=[0.0, 0.01, 0.2]
        ):
            with patch("controllers.radio.sdrforge_readiness.time.sleep"):
                with pytest.raises(SdrforgeNotReadyError):
                    wait_for_sdrforge_ready(timeout=0.1)


def test_rejects_invalid_timing():
    with pytest.raises(ValueError):
        wait_for_sdrforge_ready(interval=0)
