# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from apps.launchers.browser_launcher import BrowserKioskLauncher


DEFAULT_NETFLIX_URL = "https://www.netflix.com/browse"
DEFAULT_NETFLIX_PROFILE_PATH = (
    Path.home()
    / "snap"
    / "chromium"
    / "common"
    / "openroadcode-netflix"
)


class NetflixPlayer:
    """Launch Netflix in a dedicated Chromium application window."""

    def __init__(
        self,
        *,
        profile_path: str | Path = DEFAULT_NETFLIX_PROFILE_PATH,
        browser_candidates: tuple[str, ...] = (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
        ),
        software_rendering: bool = False,
    ) -> None:
        self._profile_path = Path(profile_path).expanduser()
        self._browser_candidates = browser_candidates
        self._software_rendering = software_rendering
        self._launcher: BrowserKioskLauncher | None = None
        self._display = ""

    def play(
        self,
        url: str,
        *,
        display: str,
        window_position: tuple[int, int] | None = None,
        window_size: tuple[int, int] | None = None,
    ) -> bool:
        """Open a Netflix URL on the requested X display."""
        normalized_url = self.validate_url(url)
        self.stop()

        launcher = BrowserKioskLauncher(
            url=normalized_url,
            process_pattern=f"--user-data-dir={self._profile_path}",
            browser_candidates=self._browser_candidates,
            kiosk=False,
            app_mode=True,
            profile_path=self._profile_path,
            window_position=window_position,
            window_size=window_size,
            startup_grace_seconds=0.2,
            window_class="OpenRoadCodeNetflix",
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
        """Stop the browser window owned by this player."""
        launcher = self._launcher
        self._launcher = None
        if launcher is not None:
            launcher.stop(self._display)
        self._display = ""

    def is_active(self) -> bool:
        """Return whether the Netflix browser process is running."""
        return (
            self._launcher is not None
            and self._launcher.is_running()
        )

    @staticmethod
    def validate_url(url: str) -> str:
        """Validate and normalize a direct Netflix HTTPS URL."""
        normalized_url = url.strip()
        parsed = urlparse(normalized_url)
        hostname = (parsed.hostname or "").casefold()
        if parsed.scheme != "https":
            raise ValueError("Netflix URL must use HTTPS")
        if hostname != "netflix.com" and not hostname.endswith(
            ".netflix.com"
        ):
            raise ValueError("URL must point to netflix.com")
        return normalized_url

    def __enter__(self) -> "NetflixPlayer":
        return self

    def __exit__(self, exception_type, exception, traceback) -> None:
        self.stop()
