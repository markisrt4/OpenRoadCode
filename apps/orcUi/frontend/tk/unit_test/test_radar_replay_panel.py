# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Radar popup state, touch dismissal and retirement without an X display."""
from unittest.mock import Mock, patch

import tkinter as tk

from apps.orcUi.frontend.tk.radar_replay_panel import RadarReplayPanel
from apps.orcUi.theme_runtime import theme_bundle
from ui.theme import ThemeMode


def panel():
    view = object.__new__(RadarReplayPanel)
    view._ui = theme_bundle(ThemeMode.DARK).ui
    view._times = ()
    view._frame_index = None
    view._on_seek = Mock()
    view._on_close = Mock()
    view._closed = False
    for name in ('_data_status', '_visibility', '_timeline', '_value', '_play',
                 '_previous', '_next', '_live', '_timestamp', '_oldest', '_edge'):
        setattr(view, name, Mock())
    view._palette_buttons = {False: (Mock(), 'Universal'), True: (Mock(), 'Classic')}
    view._source_buttons = {False: (Mock(), 'Observed'), True: (Mock(), 'Forecast')}
    view._speed_buttons = {factor: (Mock(), f'{factor:g}×') for factor in (0.5, 1.0, 2.0)}
    return view


def test_controller_updates_select_choices_and_do_not_seek():
    view = panel()
    # A Scale can invoke its command when its variable changes programmatically.
    view._value.set.side_effect = lambda value: view._scrub(str(value))
    view.render((100, 200, 300), 1, enabled=True, playing=True,
                forecast=True, classic=True, speed=2.0)
    view._on_seek.assert_not_called()
    for buttons, selected in ((view._palette_buttons, True),
                              (view._source_buttons, True), (view._speed_buttons, 2.0)):
        for key, (button, _) in buttons.items():
            assert button.configure_button.call_args.kwargs['text'].startswith('✓') == (key == selected)
    assert view._play.configure_button.call_args.kwargs['text'] == 'Ⅱ Pause'
    view.render((), None, enabled=False, playing=False)
    assert view._play.configure_button.call_args.kwargs['state'] == tk.DISABLED
    assert view._previous.configure_button.call_args.kwargs['state'] == tk.DISABLED
    assert view._next.configure_button.call_args.kwargs['state'] == tk.DISABLED


def test_steps_and_scrubbing_remain_within_available_frames():
    view = panel()
    view._times = (100, 200, 300)
    view._frame_index = 0
    view._step(-1)
    view._scrub('-1')
    view._scrub('9')
    view._on_seek.assert_not_called()
    view._step(1)
    view._on_seek.assert_called_once_with(1)
    view._frame_index = 2
    view._on_seek.reset_mock()
    view._step(1)
    view._on_seek.assert_not_called()


def test_only_outside_taps_dismiss_popup():
    view = panel()
    for name, value in (('winfo_rootx', 100), ('winfo_rooty', 100),
                         ('winfo_width', 600), ('winfo_height', 500)):
        setattr(view, name, Mock(return_value=value))
    view._outside_press(Mock(x_root=200, y_root=200))
    view._on_close.assert_not_called()
    assert view._outside_press(Mock(x_root=50, y_root=200)) == 'break'
    view._on_close.assert_called_once_with()


def test_destroy_releases_grab_once_and_leaves_other_popups_alone():
    for owns_grab in (True, False):
        view = panel()
        view.grab_current = Mock(return_value=view if owns_grab else Mock())
        view.grab_release = Mock()
        with patch('apps.orcUi.frontend.tk.radar_replay_panel.tk.Toplevel.destroy') as destroy:
            view.destroy()
            view.destroy()
            destroy.assert_called_once_with()
        assert view.grab_release.call_count == int(owns_grab)
