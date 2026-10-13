# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

"""Compose ORC music visualizer analysis sources."""

from __future__ import annotations

import os
import shutil
import sys
from common.resource_cleanup import ResourceCleanup
from collections.abc import Callable

from ui.music_visualizer import VisualizerFrame, MusicVisualizerSource
from controllers.audio.music_analysis.music_visualizer_session import MusicVisualizerSession
from controllers.audio.capture import AndroidPlaybackAudioCapture, PipewireAudioCapture


def _is_android_runtime() -> bool:
    return bool(os.getenv('TERMUX_VERSION') or os.getenv('ANDROID_ROOT')
                or os.getenv('PREFIX', '').startswith('/data/data/com.termux/'))


def selected_music_visualizer_source() -> MusicVisualizerSource:
    """Return the configured visualizer source.

    Linux hosts with PipeWire tools default to system-output capture. Other
    platforms retain simulation as the safe fallback.
    """
    default = (MusicVisualizerSource.PIPEWIRE.value
               if (sys.platform.startswith("linux") and not _is_android_runtime()
                   and shutil.which("pw-record"))
               else MusicVisualizerSource.SIMULATED.value)
    raw = os.getenv("OPENROAD_MUSIC_VISUALIZER_SOURCE", default)
    try:
        return MusicVisualizerSource(raw.strip().lower())
    except ValueError as exc:
        supported = ", ".join(source.value for source in MusicVisualizerSource)
        raise ValueError(
            f"Unsupported OPENROAD_MUSIC_VISUALIZER_SOURCE '{raw}'; expected one of: {supported}"
        ) from exc


def selected_native_visualizer_source() -> MusicVisualizerSource:
    """Prefer consented phone playback on Termux unless explicitly overridden."""
    if _is_android_runtime() and 'OPENROAD_MUSIC_VISUALIZER_SOURCE' not in os.environ:
        return MusicVisualizerSource.ANDROID_PLAYBACK
    return selected_music_visualizer_source()


def _pipewire_block_size() -> int:
    """Return the configured PipeWire capture block size."""
    raw = os.getenv("OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE", "2048")
    try:
        block_size = int(raw)
    except ValueError as exc:
        raise ValueError(
            f"OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE must be an integer, got '{raw}'"
        ) from exc
    if block_size < 2048:
        raise ValueError("OPENROAD_MUSIC_VISUALIZER_BLOCK_SIZE must be >= 2048")
    return block_size


def create_music_visualizer_session(
    callback: Callable[[VisualizerFrame], None],
    *,
    source: MusicVisualizerSource | None = None,
) -> MusicVisualizerSession | None:
    """Create the selected real-audio session, or None for simulation."""
    selected = source or selected_music_visualizer_source()
    if selected is MusicVisualizerSource.SIMULATED:
        return None

    target = os.getenv("OPENROAD_MUSIC_VISUALIZER_PIPEWIRE_TARGET") or None
    block_size = _pipewire_block_size()

    def capture_factory():
        if selected is MusicVisualizerSource.ANDROID_PLAYBACK:
            return AndroidPlaybackAudioCapture(block_size=block_size)
        return PipewireAudioCapture(target=target, block_size=block_size)

    return MusicVisualizerSession(capture_factory, callback)


def create_browser_visualizer(app):
    """Wire shared analysis and the ORC-selected browser host."""
    from apps.launchers.browser_launcher import BrowserKioskLauncher
    from apps.orcUi.adapters.music_visualizer_browser import MusicVisualizerBrowser, WINDOW_CLASS
    from common.xdg_paths import openroadcode_data_dir
    from controllers.audio.music_analysis.music_analysis_session import PushAudioCapture
    from controllers.audio.music_analysis.shared_music_analysis_session import SharedMusicAnalysisSession
    from ui.theme import ThemeMode

    sources = {"browser": PushAudioCapture}
    size = _pipewire_block_size()
    target = os.getenv("OPENROAD_MUSIC_VISUALIZER_PIPEWIRE_TARGET") or None
    if shutil.which("pw-record"):
        sources["linux-pipewire"] = lambda: PipewireAudioCapture(target=target, block_size=size)
    if _is_android_runtime():
        sources["android-playback"] = lambda: AndroidPlaybackAudioCapture(block_size=size)
    with ResourceCleanup() as cleanup:
        session = SharedMusicAnalysisSession(sources)
        cleanup.callback(session.close)
        selected = selected_music_visualizer_source()
        if "OPENROAD_MUSIC_VISUALIZER_SOURCE" not in os.environ and "android-playback" in sources:
            selected = MusicVisualizerSource.ANDROID_PLAYBACK
        name = {MusicVisualizerSource.PIPEWIRE: "linux-pipewire",
                MusicVisualizerSource.ANDROID_PLAYBACK: "android-playback"}.get(selected)
        if name in sources:
            session.select(name)
        browser = BrowserKioskLauncher(
            url="about:blank", process_pattern="music-visualizer-browser", kiosk=False, app_mode=True,
            profile_path=openroadcode_data_dir("music-visualizer-browser"),
            window_class=WINDOW_CLASS,
        )
        host = MusicVisualizerBrowser(session, browser,
                                      color_scheme=lambda: "dark" if app.theme_mode is ThemeMode.DARK else "light")
        cleanup.release()
        return host
