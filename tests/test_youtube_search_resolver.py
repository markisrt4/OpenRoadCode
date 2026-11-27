"""YouTube first-result resolver contracts."""

import json
from io import BytesIO
from unittest.mock import patch

from controllers.media.youtube_search_resolver import first_video_url


def test_first_result_opens_watch_page_with_autoplay() -> None:
    class Result:
        stdout = json.dumps({"entries": [{"id": "dQw4w9WgXcQ"}]})

    with patch("controllers.media.youtube_search_resolver.subprocess.run", return_value=Result()):
        assert first_video_url("test song") == (
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&autoplay=1"
        )


def test_missing_ytdlp_falls_back_to_search() -> None:
    with patch(
        "controllers.media.youtube_search_resolver.subprocess.run", side_effect=FileNotFoundError
    ):
        assert first_video_url("artist song") == (
            "https://www.youtube.com/results?search_query=artist+song"
        )


def test_uses_first_data_api_result_when_key_is_configured():
    with (
        patch(
            "controllers.media.youtube_search_resolver.urlopen",
            return_value=BytesIO(b'{"items":[{"id":{"videoId":"abcDEF_1234"}}]}'),
        ) as request,
        patch("controllers.media.youtube_search_resolver.subprocess.run") as fallback,
    ):
        assert first_video_url("artist song", api_key="test-key") == (
            "https://www.youtube.com/watch?v=abcDEF_1234&autoplay=1"
        )
    assert "maxResults=1" in request.call_args.args[0]
    fallback.assert_not_called()
