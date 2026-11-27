"""Managed browser operations for Trending video."""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from apps.orcUi.adapters.managed_browser_media_player import ManagedBrowserMediaPlayer
from controllers.media.youtube_search_resolver import first_video_url
from security.environment_variable_secret_manager import EnvironmentVariableSecretManager


class ManagedTrendingVideoSession:
    """Resolve one query and own the browser operations for its pane."""

    def __init__(self, player: ManagedBrowserMediaPlayer, query: str) -> None:
        self._player = player
        self._query = query
        self._closed = False
        self._started = False
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="trending-youtube")
        self._result = self._worker.submit(self._resolve)

    def _resolve(self) -> str:
        api_key = EnvironmentVariableSecretManager().get_secret("YOUTUBE_API_KEY")
        return first_video_url(self._query, api_key=api_key)

    def poll_target(self) -> str | None:
        if self._closed or not self._result.done():
            return None
        try:
            return self._result.result() or self._query
        except Exception:
            return self._query

    def play(self, target: str, position: tuple[int, int], size: tuple[int, int]) -> bool:
        if self._closed:
            return False
        self._started = self._player.play(
            target,
            display=os.environ.get("DISPLAY", ":1"),
            window_position=position,
            window_size=size,
        )
        return self._started

    def theater(self, window_id: int) -> None:
        if self._closed or not self._started:
            return
        try:
            subprocess.run(
                ["xdotool", "key", "--window", str(window_id), "t"],
                check=False,
                timeout=1,
                capture_output=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._worker.shutdown(wait=False, cancel_futures=True)
        if self._started:
            Thread(target=self._player.stop, name="trending-browser-close", daemon=True).start()
