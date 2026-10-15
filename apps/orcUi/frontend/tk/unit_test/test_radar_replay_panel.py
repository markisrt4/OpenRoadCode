# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Radar popup state, touch dismissal and retirement without an X display."""
from unittest.mock import Mock, patch

import tkinter as tk

from apps.orcUi.frontend.tk.radar_replay_panel import RadarReplayPanel, _TouchButton
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
    view._set_compact = Mock()
    for name in ('_data_status', '_visibility', '_timeline', '_compact_timeline', '_value', '_play',
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


def test_hover_and_selected_buttons_remain_distinct_in_both_themes():
    for mode in ThemeMode:
        button = object.__new__(_TouchButton)
        button._ui = theme_bundle(mode).ui
        button._button = Mock()
        button._button.cget.return_value = tk.NORMAL
        button._selected = False
        button._hovered = False
        button._paint_background()
        assert button._button.configure.call_args.kwargs['bg'] == button._ui.control_background
        button._set_hover(True)
        hover = button._button.configure.call_args.kwargs
        assert hover['bg'] == hover['activebackground'] == button._ui.border
        assert hover['bg'] != button._ui.control_active
        button._set_hover(False)
        assert button._button.configure.call_args.kwargs['bg'] == button._ui.control_background
        button.configure_button(selected=True)
        for hovered in (True, False):
            button._set_hover(hovered)
            selected = button._button.configure.call_args.kwargs
            assert selected['bg'] == selected['activebackground'] == button._ui.control_active
        button._button.cget.return_value = tk.DISABLED
        button._set_hover(True)
        assert button._button.configure.call_args.kwargs['bg'] == button._ui.control_background


def test_playback_collapses_releases_map_input_and_stop_restores_full_controls():
    view = panel()
    view._compact = False
    view._body = Mock()
    view._compact_body = Mock()
    view.grab_current = Mock(return_value=view)
    view.grab_release = Mock()
    view.grab_set = Mock()
    view.focus_set = Mock()
    view.update_idletasks = Mock()
    view.reposition = Mock()
    del view._set_compact
    view.render((100, 200, 300), 1, enabled=True, playing=True)
    assert view._compact
    view._body.pack_forget.assert_called_once()
    view._compact_body.pack.assert_called_once()
    view.grab_release.assert_called_once()
    assert view._compact_timeline.configure.call_args.kwargs['state'] == tk.NORMAL
    view._on_play = Mock()
    view._stop_compact()
    view._on_play.assert_called_once_with()
    view.render((100, 200, 300), 1, enabled=True, playing=False)
    assert not view._compact
    view._compact_body.pack_forget.assert_called_once()
    view._body.pack.assert_called_once()
    view.grab_set.assert_called_once()
    view._stop_compact()
    assert view._on_play.call_count == 1


def test_replay_frames_do_not_reposition_or_regrab_compact_bar():
    view = panel()
    view._compact = True
    view.update_idletasks = Mock()
    view.grab_set = Mock()
    view.reposition = Mock()
    RadarReplayPanel._set_compact(view, True)
    view.update_idletasks.assert_not_called()
    view.grab_set.assert_not_called()
    view.reposition.assert_not_called()


def test_compact_bar_is_positioned_at_bottom_of_map_panel():
    view = panel()
    view._compact = True
    view._owner_panel = Mock()
    for name, value in (('winfo_width', 900), ('winfo_height', 400),
                        ('winfo_rootx', 100), ('winfo_rooty', 100)):
        getattr(view._owner_panel, name).return_value = value
    view.winfo_screenwidth = Mock(return_value=1280)
    view.winfo_screenheight = Mock(return_value=720)
    view.winfo_reqheight = Mock(return_value=64)
    view.geometry = Mock()
    view.reposition()
    view.geometry.assert_called_once_with('720x64+190+424')
