# SPDX-License-Identifier: MIT
"""Tests for persisted RF display preferences."""

from adapters.radio.json_radio_visualization_settings import JsonRadioVisualizationSettings
from ui.radio.radio_visualization_config import RadioRenderer, RadioVisualizationConfig


def test_round_trip(tmp_path):
    path = tmp_path / "config" / "rf_visualization.json"
    settings = JsonRadioVisualizationSettings(path)
    saved = RadioVisualizationConfig(renderer=RadioRenderer.TK, max_fps=20, palette="grayscale")

    settings.save(saved)

    assert settings.load() == saved


def test_partial_and_invalid_saved_settings(tmp_path):
    path = tmp_path / "rf_visualization.json"
    settings = JsonRadioVisualizationSettings(path)
    defaults = RadioVisualizationConfig(renderer=RadioRenderer.OPENGL, max_fps=30)
    assert settings.load(defaults) == defaults

    path.write_text('{"palette":"grayscale","recenter_on_tune":false}', encoding="utf-8")
    assert settings.load(defaults) == RadioVisualizationConfig(
        renderer=RadioRenderer.OPENGL, max_fps=30, palette="grayscale"
    )

    path.write_text('{"max_fps":100}', encoding="utf-8")
    assert settings.load(defaults) == defaults
