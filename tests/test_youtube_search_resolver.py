"""YouTube first-result resolver contracts."""
import json
from unittest.mock import patch
from controllers.media.youtube_search_resolver import first_video_url


def test_first_result_opens_embedded_autoplay() -> None:
    class Result:
        stdout = json.dumps({"entries": [{"id": "dQw4w9WgXcQ"}]})
    with patch("controllers.media.youtube_search_resolver.subprocess.run", return_value=Result()):
        assert first_video_url("test song") == (
            "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&playsinline=1"
        )


def test_missing_ytdlp_falls_back_to_search() -> None:
    with patch("controllers.media.youtube_search_resolver.subprocess.run",
               side_effect=FileNotFoundError):
        assert first_video_url("artist song") == (
            "https://www.youtube.com/results?search_query=artist+song"
        )
