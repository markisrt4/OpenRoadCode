# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Component checks for the captioned automotive instrument."""

from __future__ import annotations

from unittest.mock import MagicMock

from frontends.tk.automotive.round_gauge_caption import RoundGauge


def _gauge() -> RoundGauge:
    gauge = object.__new__(RoundGauge)
    gauge._title = "Boost"
    gauge._unit = "psi"
    gauge._value = 12.5
    gauge._precision = 1
    gauge._connected = True
    gauge._style = MagicMock()
    gauge._style.condensed_font_family = "Sans"
    gauge._style.font_family = "Sans"
    gauge._style.mono_font_family = "Monospace"
    gauge.create_text = MagicMock()
    gauge.create_rectangle = MagicMock()
    return gauge


def test_title_is_not_drawn_inside_dial() -> None:
    gauge = _gauge()
    gauge._draw_labels(100, 100, 90)
    texts = [call.kwargs.get("text") for call in gauge.create_text.call_args_list]
    assert "BOOST" not in texts
    assert "PSI" in texts
    assert "12.5" in texts


def test_disconnected_value_is_off() -> None:
    gauge = _gauge()
    gauge._connected = False
    gauge._draw_labels(100, 100, 90)
    texts = [call.kwargs.get("text") for call in gauge.create_text.call_args_list]
    assert "OFF" in texts
