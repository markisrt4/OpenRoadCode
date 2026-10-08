# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Exercise the actual embedded host HTTP and capture lifecycle."""
import json
from urllib.request import Request, urlopen
from unittest.mock import Mock

from apps.orcUi.adapters.music_visualizer_browser import MusicVisualizerBrowser
from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession, PushAudioCapture


def test_host_serves_shared_webgl_and_releases_audio_with_browser():
    capture = PushAudioCapture()
    session = MusicAnalysisSession({'browser': lambda: capture})
    browser = Mock()
    theme = ['dark']
    host = MusicVisualizerBrowser(session, browser, color_scheme=lambda: theme[0])
    try:
        with urlopen(host.url) as response:
            html = response.read().decode()
        assert 'webgl_music_visualizer.js' in html
        assert 'music-visualizer-toggle' in html
        assert 'data-color-scheme="dark"' in html
        theme[0] = 'light'
        with urlopen(host.url) as response:
            assert b'data-color-scheme="light"' in response.read()
        theme[0] = 'dark'
        with urlopen(host.url + 'web-assets/audio-analysis/webgl_music_visualizer.js') as response:
            assert b'Frequency Tunnel' in response.read()
        with urlopen(host.url + 'api/audio-analysis/sources') as response:
            assert json.load(response)['sources'] == ['browser']
        body = json.dumps({'source': 'browser'}).encode()
        with urlopen(Request(host.url + 'api/audio-analysis/source', data=body,
                             headers={'Content-Type': 'application/json'})) as response:
            assert json.load(response)['running']
        assert capture.is_running
        host.play(host.url, display=':1', window_position=(0, 0), window_size=(800, 600))
        browser.set_url.assert_called_once_with(host.url)
        browser.launch.assert_called_once_with(':1')
        browser.set_preferred_color_scheme.assert_called_once_with('dark')
        session.start('browser')
        host.stop()
        assert not capture.is_running
        browser.stop.assert_called_with(':1')
    finally:
        host.close()
    assert not host._thread.is_alive()
    host.close()
