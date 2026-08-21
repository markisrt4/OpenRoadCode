# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""OpenRoadCode browser application bootstrap."""

import os
from pathlib import Path

from apps.webUi.lighting_session import WebLightingSession
from apps.webUi.linux_audio_analysis_session import WebLinuxAudioAnalysisSession
from apps.webUi.menu_catalog import create_web_ui_menu_pages
from apps.webUi.navigation_session import WebNavigationSession
from apps.webUi.song_recognition_session import WebSongRecognitionSession
from apps.webUi.spotify_session import WebSpotifySession
from controllers.cache import PersistentCache
from controllers.song_recognition import SongMetadataCache
from frontends.web import create_web_frontend

project_root = Path(__file__).resolve().parents[2]
navigation_session = WebNavigationSession()
spotify_session = WebSpotifySession()
lighting_session = WebLightingSession(project_root)
linux_audio_analysis_session = WebLinuxAudioAnalysisSession()
song_metadata_cache = SongMetadataCache(
    PersistentCache("~/.cache/openroadcode/song_recognition", suffix=".json")
)
song_recognition_session = WebSongRecognitionSession(metadata_cache=song_metadata_cache)
app = create_web_frontend(
    create_web_ui_menu_pages(),
    navigation_session=navigation_session,
    spotify_session=spotify_session,
    lighting_session=lighting_session,
    song_recognition_session=song_recognition_session,
    linux_audio_analysis_session=linux_audio_analysis_session,
)

if __name__ == "__main__":
    host = os.environ.get("OPENROADCODE_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("OPENROADCODE_WEB_PORT", "5000"))
    debug = os.environ.get("OPENROADCODE_WEB_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
