# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
from unittest.mock import Mock

from frontends.tk.media.music_visualizer_screen import MusicVisualizerScreen
from ui.music_visualizer import MusicVisualizerSource


def test_hiding_screen_cancels_rendering_and_requests_capture_stop():
    host, controller, panel = Mock(), Mock(), Mock()
    screen = MusicVisualizerScreen(host, on_back=Mock(), theme_bundle=Mock(),
                                   controller=controller, initial_source=MusicVisualizerSource.SIMULATED)
    screen._poll_job = 'poll'
    screen._panel = panel
    screen.hide()
    host.cancel_ui_callback.assert_called_once_with('poll')
    controller.stop.assert_called_once_with()
    panel.close.assert_called_once_with()
    assert screen._panel is None
    # The composition owns controller shutdown; closing presentation only requests stop.
    screen.close()
    controller.close.assert_not_called()


def test_source_selection_waits_for_explicit_start():
    controller = Mock()
    screen = MusicVisualizerScreen(Mock(), on_back=Mock(), theme_bundle=Mock(),
                                   controller=controller, initial_source=MusicVisualizerSource.SIMULATED)
    screen._source_name = Mock()
    screen._status = Mock()
    screen._create_panel = Mock()
    screen._select_source('android-playback', start=False)
    controller.stop.assert_called_once()
    controller.start.assert_not_called()
    screen._select_source('android-playback')
    controller.start.assert_called_once_with(MusicVisualizerSource.ANDROID_PLAYBACK)


def test_visualizer_and_drum_settings_preserve_audio_session():
    from ui.music_visualizer import KickMode
    from ui.music_visualizer.music_visualizer_types import MusicVisualizationMode, MusicVisualizerView
    controller, panel = Mock(), Mock()
    screen = MusicVisualizerScreen(Mock(), on_back=Mock(), theme_bundle=Mock(),
                                   controller=controller, initial_source=MusicVisualizerSource.ANDROID_PLAYBACK,
                                   native_controls=True)
    screen._panel = panel
    screen._mode_name = Mock()
    screen._set_options(view=MusicVisualizerView.DRUM_KIT, kick_mode=KickMode.DOUBLE,
                        drum_zoom=2.0, drum_gain=.4)
    assert panel.configure_visualizer.call_args.args[0].view is MusicVisualizerView.DRUM_KIT
    screen._select_visualizer('Orbiting Planets')
    settings = panel.configure_visualizer.call_args.args[0]
    assert settings.mode is MusicVisualizationMode.ORBITING_PLANETS
    assert settings.view is MusicVisualizerView.VISUALIZER
    assert settings.kick_mode is KickMode.DOUBLE
    assert settings.drum_zoom == 2.0
    assert settings.drum_gain == .4
    controller.start.assert_not_called()
    controller.stop.assert_not_called()


def test_stale_poll_after_hide_does_not_reschedule_or_consume_audio():
    host, controller = Mock(), Mock()
    screen = MusicVisualizerScreen(host, on_back=Mock(), theme_bundle=Mock(),
                                   controller=controller, initial_source=MusicVisualizerSource.SIMULATED)
    screen.hide()
    screen._poll()
    host.schedule_ui_callback.assert_not_called()
    controller.presentation.assert_not_called()


def test_shared_screen_hide_releases_its_view_without_interrupting_home_audio():
    controller, panel = Mock(), Mock()
    screen = MusicVisualizerScreen(Mock(), on_back=Mock(), theme_bundle=Mock(),
                                   controller=controller, initial_source=MusicVisualizerSource.ANDROID_PLAYBACK,
                                   native_controls=True, share_session=True)
    screen._panel = panel
    screen.hide()
    controller.detach_view.assert_called_once_with(screen._view_owner)
    controller.stop.assert_not_called()
