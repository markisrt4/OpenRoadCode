# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus, urlparse

from apps.launchers.browser_launcher import BrowserKioskLauncher


DEFAULT_YOUTUBE_URL = "https://www.youtube.com/"
DEFAULT_YOUTUBE_PROFILE_PATH = (
    Path.home()
    / "snap"
    / "chromium"
    / "common"
    / "openroadcode-youtube"
)


class YouTubePlayer:
    """Launch YouTube in a dedicated Chromium application window."""

    def __init__(
        self,
        *,
        profile_path: str | Path = DEFAULT_YOUTUBE_PROFILE_PATH,
        browser_candidates: tuple[str, ...] = (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ),
        software_rendering: bool = False,
        dark_mode: bool = False,
    ) -> None:
        self._profile_path = Path(profile_path).expanduser()
        self._browser_candidates = browser_candidates
        self._software_rendering = software_rendering
        self._dark_mode = dark_mode
        self._launcher: BrowserKioskLauncher | None = None
        self._display = ""

    def play(
        self,
        target: str,
        *,
        display: str,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
    ) -> bool:
        """Open a YouTube URL or search query on the requested display."""
        url = self.resolve_target(target)
        self.stop()

        launcher = BrowserKioskLauncher(
            url=url,
            process_pattern=f"--user-data-dir={self._profile_path}",
            browser_candidates=self._browser_candidates,
            kiosk=False,
            app_mode=True,
            profile_path=self._profile_path,
            window_position=window_position,
            window_size=window_size,
            startup_grace_seconds=0.2,
            window_class="OpenRoadCodeYouTube",
            extra_arguments=self._browser_arguments(),
        )
        launcher.launch(display)
        self._launcher = launcher
        self._display = display
        return True

    def _browser_arguments(self) -> tuple[str, ...]:
        arguments = [
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run",
        ]
        if self._dark_mode:
            arguments.append("--force-dark-mode")
        else:
            arguments.append("--disable-features=WebContentsForceDark")
        if self._software_rendering:
            arguments.extend(
                (
                    "--disable-gpu",
                    "--disable-gpu-compositing",
                    "--disable-features=VaapiVideoDecoder,VaapiVideoEncoder",
                )
            )
        return tuple(arguments)

    def stop(self) -> None:
        launcher = self._launcher
        self._launcher = None
        if launcher is not None:
            launcher.stop(self._display)
        self._display = ""

    def is_active(self) -> bool:
        return self._launcher is not None and self._launcher.is_running()

    @staticmethod
    def resolve_target(target: str) -> str:
        normalized = target.strip()
        if not normalized:
            return DEFAULT_YOUTUBE_URL

        parsed = urlparse(normalized)
        if not parsed.scheme:
            return (
                "https://www.youtube.com/results?search_query="
                f"{quote_plus(normalized)}"
            )

        hostname = (parsed.hostname or "").casefold()
        if parsed.scheme != "https":
            raise ValueError("YouTube URL must use HTTPS")
        if not (
            hostname == "youtube.com"
            or hostname.endswith(".youtube.com")
            or hostname == "youtu.be"
        ):
            raise ValueError("URL must point to youtube.com or youtu.be")
        return normalized
