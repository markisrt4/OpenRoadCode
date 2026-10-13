# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Display customization must preserve measurement and elapsed-time behavior."""
from dataclasses import replace
import math

import pytest

from frontends.tk.media.frequency_analyzer_scene import (
    AnalyzerDisplay, PLOT_BOTTOM, PLOT_HEIGHT, analyzer_color, measured_levels,
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


def test_presentation_gain_reveals_quiet_input_without_changing_frame():
    quiet = replace(LOUD, spectrum_dbfs=(-74.0,))

    assert max(measured_levels(quiet)) == 0
    assert max(measured_levels(quiet, gain_db=24)) == pytest.approx(1 / 6)
    assert quiet.spectrum_dbfs == (-74.0,)


def test_response_is_elapsed_time_based_not_render_frame_count():
    options = AnalyzerAppearance(response_s=.2, gain_db=0)
    once, twice = AnalyzerDisplay(), AnalyzerDisplay()
    for display in (once, twice):
        display.update(SILENT, options, 0, True)
    once.update(LOUD, options, .2, True)
    twice.update(LOUD, options, .1, True)
    twice.update(LOUD, options, .2, True)
    assert once.levels == pytest.approx(twice.levels)
    assert max(once.levels) == pytest.approx(.8 * (1-math.exp(-1)))


def test_decay_and_peak_hold_do_not_fabricate_new_audio_when_stale():
    options = AnalyzerAppearance(response_s=0, decay_s=.3, gain_db=0)
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
    assert AnalyzerAppearance().palette is AnalyzerPalette.RETRO
    assert not AnalyzerAppearance().segmented


@pytest.mark.parametrize('palette', list(AnalyzerPalette))
def test_smooth_render_preserves_height_and_gradient_with_bounded_geometry(palette):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from frontends.tk.media.frequency_analyzer_scene import draw_analyzer
    options = AnalyzerAppearance(palette=palette)
    display = AnalyzerDisplay()
    display.levels = [.25, .75] * 32
    gl = Mock(GL_QUADS=7, GL_LINES=1)
    state = SimpleNamespace(primitive=None, color=None)
    vertices = []
    gl.glBegin.side_effect = lambda primitive: setattr(state, 'primitive', primitive)
    gl.glColor3f.side_effect = lambda *color: setattr(state, 'color', color)

    def vertex(x, y):
        if state.primitive == gl.GL_QUADS:
            vertices.append((x, y, state.color))

    gl.glVertex2f.side_effect = vertex
    draw_analyzer(gl, SILENT, 1, options, display)
    # Smooth rendering must not grow into dozens of strips per frequency band.
    assert len(vertices) <= 64 * 8
    quads = [vertices[i:i+4] for i in range(0, len(vertices), 4)]
    for i, height in enumerate(display.levels):
        center = .04 + .92 * (i+.5) / 64
        column = [quad for quad in quads
                  if (quad[0][0]+quad[1][0])/2 == pytest.approx(center)]
        assert min(v[1] for q in column for v in q) == pytest.approx(PLOT_BOTTOM)
        assert max(v[1] for q in column for v in q) == pytest.approx(PLOT_BOTTOM + height * PLOT_HEIGHT)
        assert column[0][0][2] == pytest.approx(analyzer_color(options, 0))
        assert column[-1][2][2] == pytest.approx(analyzer_color(options, 1))
        for previous, following in zip(column, column[1:]):
            assert previous[2][1] == pytest.approx(following[0][1])
            assert previous[2][2] == pytest.approx(following[0][2])
        if palette is AnalyzerPalette.RETRO:
            assert column[0][2][2] == (1, 1, .04)


def test_bar_style_does_not_change_response_or_peak_timing():
    smooth, segmented = AnalyzerDisplay(), AnalyzerDisplay()
    options = AnalyzerAppearance()
    for now, frame in ((0, SILENT), (.04, LOUD), (.09, LOUD), (.15, SILENT), (.7, SILENT)):
        smooth.update(frame, options, now, True)
        segmented.update(frame, replace(options, segmented=True), now, True)
        assert smooth.levels == segmented.levels
        assert smooth.peaks == segmented.peaks


def test_wide_bars_regroup_real_bins_and_reset_display_without_changing_scale():
    frame = replace(SILENT, spectrum_hz=(100, 110, 1000), spectrum_dbfs=(-30, -12, -24))
    narrow = measured_levels(frame, 64)
    wide = measured_levels(frame, 8)
    assert len(narrow) == 64 and len(wide) == 8
    assert max(wide) == pytest.approx(.8)
    assert max(narrow) == pytest.approx(.8)
    display = AnalyzerDisplay()
    display.update(frame, AnalyzerAppearance(gain_db=0), 0, True)
    display.update(frame, AnalyzerAppearance(band_count=8, gain_db=0), .1, True)
    assert len(display.levels) == len(display.peaks) == 8
    assert display.levels == pytest.approx(wide)
