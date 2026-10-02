# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Exercise actual embedded Chromium choices and audio using a synthetic microphone.

Requires an X11 session, Chromium, xdotool, and optional Python playwright.
Run: python -m apps.orcUi.component_test.music_visualizer_browser_cli
"""
import argparse
import math
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import time
import wave


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--software-rendering', action='store_true')
    parser.add_argument('--no-sandbox', action='store_true', help='Only for isolated test environments requiring this flag')
    args = parser.parse_args()
    from playwright.sync_api import sync_playwright
    from apps.orcUi.composition.application import create_orc_ui_composition

    with TemporaryDirectory(prefix='orc-visualizer-test-') as directory:
        tone = Path(directory) / 'tone.wav'
        with wave.open(str(tone), 'wb') as audio:
            audio.setparams((1, 2, 48000, 0, 'NONE', ''))
            audio.writeframes(b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * 1000 * i / 48000)))
                                       for i in range(48000)))
        composition = create_orc_ui_composition()
        app = composition.app
        runtime = composition.media.visualizer_runtime
        try:
            runtime._browser.profile_path = Path(directory) / 'browser'
            flags = ['--remote-debugging-port=0', '--use-fake-device-for-media-stream',
                     '--use-fake-ui-for-media-stream', f'--use-file-for-fake-audio-capture={tone}']
            if args.software_rendering:
                flags += ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']
            if args.no_sandbox:
                flags += ['--no-sandbox']
            runtime._browser.extra_arguments = tuple(flags)
            app._root.attributes('-fullscreen', False)
            app._root.minsize(1024, 600)
            app._root.geometry('1024x600')
            app._root.update()
            app.navigate_to('VISUALIZER')
            for _ in range(30):
                app._root.update()
                time.sleep(.02)
            screen = composition.media.visualizer
            assert screen._embedder.window_id, 'Browser was not embedded'
            marker = runtime._browser.profile_path / 'DevToolsActivePort'
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            port = int(marker.read_text().splitlines()[0])
            with sync_playwright() as playwright:
                browser = playwright.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
                page = next(page for context in browser.contexts for page in context.pages
                            if page.url.startswith(runtime.url))
                page.locator('#music-visualizer-source-button').click()
                page.locator('#music-visualizer-source-choices button[data-value="browser"]').click()
                page.locator('#music-visualizer-toggle').click()
                page.wait_for_function("parseFloat(document.getElementById('music-mid').style.width)>0")
                assert page.evaluate('innerWidth>500 && innerHeight>250')
                count = page.locator('#mv-webgl-mode option').count()
                assert count == 13
                for index in range(count):
                    page.locator('#mv-webgl-mode-button').click()
                    page.locator('#mv-webgl-mode-choices button').nth(index).click()
                    assert page.locator('#mv-webgl-mode').evaluate('(select)=>select.selectedIndex') == index
                page.locator('#music-zeroize-start').click()
                page.wait_for_function("document.getElementById('music-zeroize-finish').disabled===false")
                page.wait_for_timeout(200)
                page.locator('#music-zeroize-finish').click()
                page.wait_for_function("document.getElementById('music-zeroize-status').textContent.includes('calibration active')")
                capture = runtime._session._capture
                assert runtime._session.state()['zeroized']
                page.locator('#music-view-drums').click()
                assert page.locator('#music-drum-kit').is_visible()
                assert not page.locator('#mv-webgl-stage').is_visible()
                page.locator('[data-kick-mode="double"]').click()
                assert page.locator('#drum-kick-right').is_visible()
                page.locator('#music-view-visualization').click()
                page.locator('#music-view-drums').click()
                assert page.evaluate('OpenRoadCodeWeb.KickMode.mode') == 'double'
                page.locator('[data-kick-mode="single"]').click()
                assert not page.locator('#drum-kick-right').is_visible()
                assert page.locator('#mv-seg-kick .mv-segment').count() == 8
                page.locator('#music-view-visualization').click()
                assert page.locator('#mv-webgl-stage').is_visible()
                assert runtime._session._capture is capture
                assert runtime._session.state()['running'] and runtime._session.state()['zeroized']
                page.locator('#music-zeroize-clear').click()
                page.locator('#music-view-drums').click()
                page.wait_for_function("""[...document.querySelectorAll('.mv-segment')].some(
                    meter=>meter.style.background && meter.style.background!=='rgb(22, 32, 42)')""")
                page.locator('#music-view-visualization').click()
                page.locator('#mv-webgl-fullscreen').click()
                page.wait_for_function('document.fullscreenElement!==null')
                page.locator('#mv-webgl-mode-button').click()
                page.locator('#mv-webgl-mode-choices button').nth(2).click()
                page.locator('#mv-webgl-fullscreen').click()
                app.navigate_to('MEDIA')
                app._root.update()
                assert not runtime._session.state()['running']
                assert not runtime.is_active()
            print('PASS: embedded X11 viewport, PCM analysis, all preset menus, drum views/kick controls, preserved capture/calibration, fullscreen, cleanup')
        finally:
            composition.media.close()
            composition.games.shutdown()
            composition.core.close()
            composition.runtime.close()
            app._root.destroy()


if __name__ == '__main__':
    main()
