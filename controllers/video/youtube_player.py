# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-backed YouTube application controller."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus, urlparse

from apps.launchers.browser_launcher import BrowserKioskLauncher

DEFAULT_YOUTUBE_URL="https://www.youtube.com/"
DEFAULT_YOUTUBE_PROFILE_PATH=Path.home()/"snap"/"chromium"/"common"/"openroadcode-youtube"


class YouTubePlayer:
    """Own a dedicated browser lifecycle for YouTube presentation."""
    def __init__(self,*,profile_path:str|Path=DEFAULT_YOUTUBE_PROFILE_PATH,browser_candidates:tuple[str,...]=("google-chrome","google-chrome-stable","chromium","chromium-browser"),software_rendering:bool=False,dark_mode:bool=False)->None:
        """Configure a YouTube player.

        @param profile_path Persistent browser profile used for YouTube sessions.
        @param browser_candidates Browser executables in preference order.
        @param software_rendering Disable GPU paths for compatibility when true.
        @param dark_mode Request browser dark presentation when true.
        """
        self._profile_path=Path(profile_path).expanduser(); self._browser_candidates=browser_candidates; self._software_rendering=software_rendering; self._dark_mode=dark_mode; self._launcher:BrowserKioskLauncher|None=None; self._display=""
    def play(self,target:str,*,display:str,window_position:tuple[int,int]|None=None,window_size:tuple[int,int]|None=None)->bool:
        """Open a YouTube URL or search query.

        @param target YouTube HTTPS URL or search text.
        @param display X11 display used by the browser.
        @param window_position Optional initial X/Y position.
        @param window_size Optional initial width/height.
        @return ``True`` after the browser launch request succeeds.
        """
        url=self.resolve_target(target); self.stop(); launcher=BrowserKioskLauncher(url=url,process_pattern=f"--user-data-dir={self._profile_path}",browser_candidates=self._browser_candidates,kiosk=False,app_mode=True,profile_path=self._profile_path,window_position=window_position,window_size=window_size,startup_grace_seconds=0.2,window_class="OpenRoadCodeYouTube",extra_arguments=self._browser_arguments()); launcher.launch(display); self._launcher=launcher; self._display=display; return True
    def _browser_arguments(self)->tuple[str,...]:
        arguments=["--autoplay-policy=no-user-gesture-required","--no-first-run"]
        arguments.append("--force-dark-mode" if self._dark_mode else "--disable-features=WebContentsForceDark")
        if self._software_rendering:arguments.extend(("--disable-gpu","--disable-gpu-compositing","--disable-features=VaapiVideoDecoder,VaapiVideoEncoder"))
        return tuple(arguments)
    def stop(self)->None:
        """Stop the browser process owned by this player."""
        launcher=self._launcher; self._launcher=None
        if launcher is not None:launcher.stop(self._display)
        self._display=""
    def is_active(self)->bool:
        """Return whether the owned YouTube browser process is running."""
        return self._launcher is not None and self._launcher.is_running()
    @staticmethod
    def resolve_target(target:str)->str:
        """Convert search text to a YouTube URL or validate a direct URL.

        @param target Search text or direct YouTube URL.
        @return Valid YouTube HTTPS URL.
        @throws ValueError When a direct URL is non-HTTPS or outside YouTube.
        """
        normalized=target.strip()
        if not normalized:return DEFAULT_YOUTUBE_URL
        parsed=urlparse(normalized)
        if not parsed.scheme:return f"https://www.youtube.com/results?search_query={quote_plus(normalized)}"
        hostname=(parsed.hostname or "").casefold()
        if parsed.scheme!="https":raise ValueError("YouTube URL must use HTTPS")
        if not(hostname=="youtube.com" or hostname.endswith(".youtube.com") or hostname=="youtu.be"):raise ValueError("URL must point to youtube.com or youtu.be")
        return normalized
