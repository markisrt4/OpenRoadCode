# SPDX-License-Identifier: MIT
"""Tests for the SDRForge RF configuration transport adapter."""

from __future__ import annotations

import io
import json
from unittest.mock import Mock

from adapters.radio import sdrforge_rf_hardware_config as module


class _ImmediateThread:
    def __init__(self, *, target, **_kwargs):
        self._target = target

    def start(self):
        self._target()


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_load_receiver_configuration(monkeypatch):
    monkeypatch.setattr(module.threading, "Thread", _ImmediateThread)
    seen = {}
    monkeypatch.setattr(
        module.request, "urlopen",
        lambda url, timeout: (
            seen.update(url=url, timeout=timeout)
            or _Response(json.dumps({"gain_db": 29.7}).encode())
        ),
    )
    success, error = Mock(), Mock()
    module.SdrForgeRfHardwareConfig().load(success, error)
    success.assert_called_once_with({"gain_db": 29.7})
    error.assert_not_called()
    assert seen == {"url": "http://127.0.0.1:5570/v1/rf/config", "timeout": 3.0}


def test_apply_receiver_configuration(monkeypatch):
    monkeypatch.setattr(module.threading, "Thread", _ImmediateThread)
    requests = []
    def respond(req, timeout):
        requests.append((req, timeout))
        return _Response(b"{}")
    monkeypatch.setattr(module.request, "urlopen", respond)
    success, error = Mock(), Mock()
    config = {"sample_rate_hz": 2400000, "gain_db": None,
              "ppm_correction": 0, "rtl_agc_enabled": False}
    module.SdrForgeRfHardwareConfig("http://localhost:5570/").apply(
        config, success, error)
    success.assert_called_once_with()
    error.assert_not_called()
    req, timeout = requests[0]
    assert req.full_url == "http://localhost:5570/v1/rf/config"
    assert req.get_method() == "POST"
    assert json.loads(req.data) == config
    assert timeout == 5.0


def test_unavailable_service_reports_error(monkeypatch):
    monkeypatch.setattr(module.threading, "Thread", _ImmediateThread)
    def unavailable(*_args, **_kwargs):
        raise OSError("connection refused")
    monkeypatch.setattr(module.request, "urlopen", unavailable)
    success, error = Mock(), Mock()
    module.SdrForgeRfHardwareConfig().load(success, error)
    success.assert_not_called()
    error.assert_called_once_with("connection refused")
