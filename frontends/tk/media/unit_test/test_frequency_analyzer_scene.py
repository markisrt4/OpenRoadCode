# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Display customization must preserve measurement and elapsed-time behavior."""
from dataclasses import replace
import math

import pytest

from frontends.tk.media.frequency_analyzer_scene import (
    AnalyzerDisplay, analyzer_color, measured_levels,
)
from ui.music_visualizer import VisualizerFrame
from ui.music_visualizer.music_visualizer_types import AnalyzerAppearance, AnalyzerPalette


SILENT = VisualizerFrame(0, 0, 0, 0, ())
LOUD = replace(SILENT, spectrum_hz=(1000.0,), spectrum_dbfs=(-12.0,))


def test_display_uses_fixed_dbfs_and_empty_bands_stay_empty():
    levels = measured_levels(LOUD)
    assert max(levels) == pytest.approx(.8)
    assert sum(value > 0 for value in levels) == 1
    assert max(measured_levels(replace(LOUD, spectrum_dbfs=(-18.0,)))) == pytest.approx(.7)
    assert measured_levels(SILENT) == [0] * 64


def test_response_is_elapsed_time_based_not_render_frame_count():
    options = AnalyzerAppearance(response_s=.2)
    once, twice = AnalyzerDisplay(), AnalyzerDisplay()
    for display in (once, twice):
        display.update(SILENT, options, 0, True)
    once.update(LOUD, options, .2, True)
    twice.update(LOUD, options, .1, True)
    twice.update(LOUD, options, .2, True)
    assert once.levels == pytest.approx(twice.levels)
    assert max(once.levels) == pytest.approx(.8 * (1-math.exp(-1)))


def test_decay_and_peak_hold_do_not_fabricate_new_audio_when_stale():
    options = AnalyzerAppearance(response_s=0, decay_s=.3)
    display = AnalyzerDisplay()
    display.update(LOUD, options, 0, True)
    display.update(LOUD, options, .3, False)
    assert max(display.levels) == pytest.approx(.8 / math.e)
    assert max(display.peaks) == pytest.approx(.8)
    display.update(LOUD, options, .7, False)
    assert max(display.peaks) < .8
    assert max(display.peaks) >= max(display.levels)
    display.update(LOUD, options, 30, False)
    assert max(display.levels) < 1e-6
    assert max(display.peaks) < 1e-6


def test_color_presets_and_custom_gradients_preserve_endpoints():
    custom = AnalyzerAppearance(palette=AnalyzerPalette.CUSTOM,
                                low_color=(.1, .2, .3), high_color=(.7, .8, .9))
    assert analyzer_color(custom, 0) == pytest.approx(custom.low_color)
    assert analyzer_color(custom, 1) == pytest.approx(custom.high_color)
    assert analyzer_color(custom, .5) == pytest.approx((.4, .5, .6))
    retro = replace(custom, palette=AnalyzerPalette.RETRO)
    assert analyzer_color(retro, 0) == (0, 1, .04)
    assert analyzer_color(retro, .5) == (1, 1, .04)
    assert analyzer_color(retro, 1) == (1, 0, .04)
    assert AnalyzerAppearance().palette is AnalyzerPalette.ORC
    assert not AnalyzerAppearance().segmented
