# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .music_video_if import MusicVideoIf
from .music_video_types import MusicVideo, MusicVideoQuery

from security.environment_variable_secret_manager import (
    EnvironmentVariableSecretManager,
)
from security.secret_manager_if import SecretManagerIf

_YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
_YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
_ISO_8601_DURATION = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


@dataclass(frozen=True)
class _Candidate:
    video: MusicVideo
    score: int


class YouTubeMusicVideo(MusicVideoIf):
    """Find and present music videos using YouTube."""

    def __init__(
        self,
        secret_manager: SecretManagerIf | None = None,
        *,
        api_key_secret_name: str = "YOUTUBE_API_KEY",
        max_search_results: int = 10,
        region_code: str = "US",
        host: str = "127.0.0.1",
        port: int = 8768,
        fullscreen: bool = False,
        chromium_executable: str | None = None,
        software_rendering: bool = False,
    ) -> None:
        if not 1 <= max_search_results <= 50:
            raise ValueError("max_search_results must be between 1 and 50")
        if len(region_code) != 2:
            raise ValueError("region_code must be a two-letter country code")

        self._secret_manager = (
            secret_manager
            if secret_manager is not None
            else EnvironmentVariableSecretManager()
        )

        self._api_key_secret_name = api_key_secret_name
        self._max_search_results = max_search_results
        self._region_code = region_code.upper()
        self._host = host
        self._port = port
        self._fullscreen = fullscreen
        self._chromium_executable = chromium_executable
        self._software_rendering = software_rendering

        self._server: ThreadingHTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._browser_process: subprocess.Popen[Any] | None = None
        self._temporary_directory: tempfile.TemporaryDirectory[str] | None = None
        self._ranked_video_ids: list[str] = []

    def find_video(self, query: MusicVideoQuery) -> MusicVideo | None:
        api_key = self._get_api_key()
        payload = self._get_json(
            _YOUTUBE_SEARCH_URL,
            {
                "part": "snippet",
                "q": f"{query.artist} {query.title} official music video",
                "type": "video",
                "videoEmbeddable": "true",
                "videoSyndicated": "true",
                "maxResults": str(self._max_search_results),
                "regionCode": self._region_code,
                "safeSearch": "moderate",
                "key": api_key,
            },
        )

        items = payload.get("items", [])
        if not isinstance(items, list) or not items:
            return None

        video_ids = [
            item.get("id", {}).get("videoId")
            for item in items
            if isinstance(item, dict)
        ]
        video_ids = [value for value in video_ids if isinstance(value, str)]
        durations, embeddable_video_ids = self._fetch_video_details(
            video_ids,
            api_key,
        )
        candidates: list[_Candidate] = []

        for item in items:
            if not isinstance(item, dict):
                continue
            identifier = item.get("id")
            snippet = item.get("snippet")
            if not isinstance(identifier, dict) or not isinstance(snippet, dict):
                continue

            video_id = identifier.get("videoId")
            title = snippet.get("title")
            channel_name = snippet.get("channelTitle")
            if not all(isinstance(v, str) and v for v in (video_id, title, channel_name)):
                continue
            if video_id not in embeddable_video_ids:
                continue

            decoded_title = html.unescape(title)
            decoded_channel = html.unescape(channel_name)
            video = MusicVideo(
                video_id=video_id,
                title=decoded_title,
                channel_name=decoded_channel,
                thumbnail_url=self._extract_thumbnail_url(snippet),
                duration_ms=durations.get(video_id),
                is_official=self._looks_official(
                    decoded_title,
                    decoded_channel,
                    query.artist,
                ),
            )
            candidates.append(_Candidate(video, self._score_candidate(video, query)))

        if not candidates:
            self._ranked_video_ids = []
            return None

        ranked_candidates = sorted(
            candidates,
            key=lambda candidate: candidate.score,
            reverse=True,
        )
        self._ranked_video_ids = [
            candidate.video.video_id for candidate in ranked_candidates
        ]
        return ranked_candidates[0].video

    def play_video(self, video: MusicVideo, position_ms: int = 0) -> bool:
        if not video.video_id:
            raise ValueError("video.video_id cannot be empty")
        if position_ms < 0:
            raise ValueError("position_ms cannot be negative")

        self.stop_video()
        chromium = self._find_chromium()
        if chromium is None:
            raise RuntimeError(
                "Chromium was not found. Install chromium or provide "
                "chromium_executable."
            )

        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="youtube-music-video-"
        )
        document_root = Path(self._temporary_directory.name)
        fallback_video_ids = (
            self._ranked_video_ids
            if video.video_id in self._ranked_video_ids
            else [video.video_id]
        )
        (document_root / "index.html").write_text(
            self._build_player_html(
                video.video_id,
                position_ms,
                fallback_video_ids,
            ),
            encoding="utf-8",
        )

        handler = self._make_request_handler(
            document_root,
            close_callback=self.stop_video,
        )
        try:
            self._server = ThreadingHTTPServer((self._host, self._port), handler)
        except OSError:
            self._cleanup()
            raise

        self._server_thread = threading.Thread(
            target=self._server.serve_forever,
            name="youtube-music-video-http",
            daemon=True,
        )
        self._server_thread.start()

        url = f"http://{self._host}:{self._port}/index.html"
        command = [
            chromium,
            f"--app={url}",
            "--autoplay-policy=no-user-gesture-required",
            "--no-first-run",
            "--disable-session-crashed-bubble",
        ]
        if self._software_rendering:
            command.extend(
                (
                    "--disable-gpu",
                    "--disable-gpu-compositing",
                    "--disable-features=VaapiVideoDecoder,VaapiVideoEncoder",
                )
            )
        if self._fullscreen:
            command.append("--start-fullscreen")

        try:
            self._browser_process = subprocess.Popen(command)
        except OSError:
            self._cleanup()
            raise

        return True

    def stop_video(self) -> None:
        if self._browser_process is not None and self._browser_process.poll() is None:
            self._browser_process.terminate()
            try:
                self._browser_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._browser_process.kill()
                self._browser_process.wait(timeout=3)
        self._cleanup()

    def is_video_active(self) -> bool:
        return self._browser_process is not None and self._browser_process.poll() is None

    def _fetch_video_details(
        self,
        video_ids: list[str],
        api_key: str,
    ) -> tuple[dict[str, int], set[str]]:
        if not video_ids:
            return {}, set()
        payload = self._get_json(
            _YOUTUBE_VIDEOS_URL,
            {
                "part": "contentDetails,status",
                "id": ",".join(video_ids),
                "key": api_key,
            },
        )
        durations: dict[str, int] = {}
        embeddable_video_ids: set[str] = set()
        for item in payload.get("items", []):
            if not isinstance(item, dict):
                continue
            video_id = item.get("id")
            details = item.get("contentDetails")
            status = item.get("status")
            if not isinstance(video_id, str):
                continue
            if isinstance(status, dict) and status.get("embeddable") is True:
                embeddable_video_ids.add(video_id)
            if isinstance(details, dict):
                duration = details.get("duration")
                if isinstance(duration, str):
                    duration_ms = self._parse_duration_ms(duration)
                    if duration_ms is not None:
                        durations[video_id] = duration_ms
        return durations, embeddable_video_ids

    def _get_api_key(self) -> str:
        try:
            return self._secret_manager.require_secret(
                self._api_key_secret_name
            )
        except RuntimeError as error:
            raise RuntimeError(
                "The YouTube Data API key is unavailable. "
                f"Expected secret: {self._api_key_secret_name}"
            ) from error

    @staticmethod
    def _score_candidate(video: MusicVideo, query: MusicVideoQuery) -> int:
        title = video.title.casefold()
        channel = video.channel_name.casefold()
        artist = query.artist.casefold().strip()
        track = query.title.casefold().strip()
        score = 0

        if artist and artist in title:
            score += 35
        if track and track in title:
            score += 45
        if "official music video" in title:
            score += 35
        elif "official video" in title:
            score += 25
        elif "music video" in title:
            score += 15
        if video.is_official:
            score += 25
        if artist and artist in channel:
            score += 15

        penalties = {
            "official audio": 15,
            "lyrics": 12,
            "lyric video": 20,
            "live": 18,
            "cover": 45,
            "reaction": 60,
            "karaoke": 55,
            "remix": 20,
            "sped up": 50,
            "slowed": 50,
        }
        for phrase, penalty in penalties.items():
            if phrase in title:
                score -= penalty

        if query.duration_ms is not None and video.duration_ms is not None:
            difference_ms = abs(query.duration_ms - video.duration_ms)
            if difference_ms <= 5_000:
                score += 25
            elif difference_ms <= 15_000:
                score += 15
            elif difference_ms <= 30_000:
                score += 5
            elif difference_ms >= 120_000:
                score -= 30
        return score

    @staticmethod
    def _looks_official(title: str, channel_name: str, artist: str) -> bool:
        title_cf = title.casefold()
        channel_cf = channel_name.casefold()
        artist_cf = artist.casefold().strip()
        return (
            "official music video" in title_cf
            or "official video" in title_cf
            or channel_cf.endswith("vevo")
            or channel_cf.endswith(" - topic")
            or bool(artist_cf and artist_cf in channel_cf)
        )

    @staticmethod
    def _extract_thumbnail_url(snippet: dict[str, Any]) -> str | None:
        thumbnails = snippet.get("thumbnails")
        if not isinstance(thumbnails, dict):
            return None
        for size in ("maxres", "standard", "high", "medium", "default"):
            thumbnail = thumbnails.get(size)
            if isinstance(thumbnail, dict):
                url = thumbnail.get("url")
                if isinstance(url, str) and url:
                    return url
        return None

    @staticmethod
    def _parse_duration_ms(value: str) -> int | None:
        match = _ISO_8601_DURATION.fullmatch(value)
        if match is None:
            return None
        days = int(match.group("days") or 0)
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)
        return (days * 86_400 + hours * 3_600 + minutes * 60 + seconds) * 1_000

    @staticmethod
    def _get_json(url: str, parameters: dict[str, str]) -> dict[str, Any]:
        request_url = f"{url}?{urllib.parse.urlencode(parameters)}"
        request = urllib.request.Request(request_url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"YouTube API request failed with HTTP {error.code}: {details}"
            ) from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"YouTube API request failed: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise RuntimeError("YouTube API returned invalid JSON") from error

        if not isinstance(value, dict):
            raise RuntimeError("YouTube API returned an unexpected response")
        return value

    def _find_chromium(self) -> str | None:
        if self._chromium_executable is not None:
            return self._chromium_executable
        for candidate in (
            "chromium",
            "chromium-browser",
            "google-chrome",
            "google-chrome-stable",
        ):
            executable = shutil.which(candidate)
            if executable is not None:
                return executable
        return None

    @staticmethod
    def _make_request_handler(
        document_root: Path,
        *,
        close_callback: Callable[[], None],
    ) -> type[SimpleHTTPRequestHandler]:
        class QuietRequestHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                super().__init__(*args, directory=str(document_root), **kwargs)

            def do_POST(self) -> None:
                if self.path != "/close":
                    self.send_error(404)
                    return

                self.send_response(204)
                self.end_headers()
                threading.Thread(
                    target=close_callback,
                    name="youtube-music-video-close",
                    daemon=True,
                ).start()

            def log_message(self, format_string: str, *args: Any) -> None:
                return

        return QuietRequestHandler

    def _cleanup(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        self._server = None
        self._server_thread = None
        self._browser_process = None
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
        self._temporary_directory = None

    def _build_player_html(
        self,
        video_id: str,
        position_ms: int,
        fallback_video_ids: list[str] | None = None,
    ) -> str:
        start_seconds = position_ms / 1_000
        origin = f"http://{self._host}:{self._port}"
        candidate_video_ids = list(
            dict.fromkeys(fallback_video_ids or [video_id])
        )
        if video_id in candidate_video_ids:
            candidate_video_ids.remove(video_id)
        candidate_video_ids.insert(0, video_id)
        return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<meta name=\"referrer\" content=\"strict-origin-when-cross-origin\">
<title>YouTube Music Video</title>
<style>
html, body, #player {{ width: 100%; height: 100%; margin: 0; overflow: hidden; background: black; }}
#message {{ position: fixed; left: 16px; bottom: 16px; z-index: 10; display: none; padding: 8px 12px; border-radius: 6px; color: white; background: rgba(0,0,0,.72); font-family: sans-serif; }}
#return-to-carui {{ position: fixed; top: 16px; right: 16px; z-index: 20; padding: 14px 20px; border: 2px solid rgba(255,255,255,.8); border-radius: 8px; color: white; background: rgba(0,0,0,.78); font: bold 16px sans-serif; cursor: pointer; }}
#return-to-carui:active {{ background: rgba(180,0,0,.9); }}
</style>
</head>
<body>
<div id=\"player\"></div>
<div id=\"message\"></div>
<button id=\"return-to-carui\" type=\"button\">RETURN</button>
<script>
const videoId = {json.dumps(video_id)};
const candidateVideoIds = {json.dumps(candidate_video_ids)};
const startSeconds = {start_seconds};
const playerOrigin = {json.dumps(origin)};
let candidateIndex = 0;
let player;
document.getElementById(\"return-to-carui\").addEventListener(
    \"click\",
    async () => {{
        const button = document.getElementById(\"return-to-carui\");
        button.disabled = true;
        button.textContent = \"CLOSING...\";
        try {{
            await fetch(\"/close\", {{ method: \"POST\" }});
        }} catch (_error) {{
            window.close();
        }}
    }}
);
function showMessage(text) {{
    const message = document.getElementById(\"message\");
    message.textContent = text;
    message.style.display = \"block\";
}}
function handlePlaybackError(event) {{
    candidateIndex += 1;
    if (candidateIndex < candidateVideoIds.length) {{
        showMessage(
            \"That video cannot be embedded. Trying another match (\" +
            (candidateIndex + 1) + \"/\" + candidateVideoIds.length + \").\"
        );
        player.loadVideoById({{
            videoId: candidateVideoIds[candidateIndex],
            startSeconds: Math.floor(startSeconds)
        }});
        return;
    }}

    player.destroy();
    const playerElement = document.getElementById(\"player\");
    playerElement.style.display = \"grid\";
    playerElement.style.placeItems = \"center\";
    playerElement.style.color = \"white\";
    playerElement.style.fontFamily = \"sans-serif\";
    playerElement.textContent =
        \"No matching YouTube video is available for in-app playback.\";
    showMessage(\"YouTube playback error: \" + event.data);
}}
function onYouTubeIframeAPIReady() {{
    player = new YT.Player(\"player\", {{
        width: \"100%\",
        height: \"100%\",
        videoId: videoId,
        playerVars: {{ autoplay: 1, controls: 1, enablejsapi: 1, playsinline: 1, rel: 0, start: Math.floor(startSeconds), origin: playerOrigin }},
        events: {{
            onReady: (event) => {{
                if (startSeconds > 0) event.target.seekTo(startSeconds, true);
                event.target.playVideo();
            }},
            onError: handlePlaybackError,
            onAutoplayBlocked: () => showMessage(\"Autoplay was blocked. Tap the video to play.\")
        }}
    }});
}}
const apiScript = document.createElement(\"script\");
apiScript.src = \"https://www.youtube.com/iframe_api\";
document.head.appendChild(apiScript);
</script>
</body>
</html>"""

    def __enter__(self) -> "YouTubeMusicVideo":
        return self

    def __exit__(self, exception_type: Any, exception: Any, traceback: Any) -> None:
        self.stop_video()
