# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Unit tests for the WebUI music-reactive lighting control surface."""
from __future__ import annotations

import pytest

from apps.webUi.music_reactive_lighting_session import WebMusicReactiveLightingSession
from controllers.lighting import DummyLightingController, MusicReactiveLighting


def test_unconfigured_session_reports_unavailable() -> None:
    session = WebMusicReactiveLightingSession()

    assert session.state() == {
        "available": False,
        "enabled": False,
        "connected": False,
    }

    with pytest.raises(RuntimeError, match="unavailable"):
        session.set_enabled(True)


def test_session_controls_reactive_lighting() -> None:
    controller = DummyLightingController()
    reactive = MusicReactiveLighting(controller)
    session = WebMusicReactiveLightingSession(reactive)

    assert session.state() == {
        "available": True,
        "enabled": False,
        "connected": False,
    }

    controller.connect().result()
    assert session.set_enabled(True) == {
        "available": True,
        "enabled": True,
        "connected": True,
    }

    assert session.set_enabled(False)["enabled"] is False
