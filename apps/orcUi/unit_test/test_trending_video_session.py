"""Trending video search remains inert after its pane closes."""

from concurrent.futures import Future
from unittest.mock import Mock

from apps.orcUi.adapters import trending_video_session


def test_late_search_cannot_start_playback_after_close(monkeypatch):
    result = Future()
    assert result.set_running_or_notify_cancel()
    worker = Mock()
    worker.submit.return_value = result
    monkeypatch.setattr(trending_video_session, "ThreadPoolExecutor", Mock(return_value=worker))
    player = Mock()
    session = trending_video_session.ManagedTrendingVideoSession(player, "artist song")

    assert session.poll_target() is None
    session.close()
    result.set_result("https://example.test/video")

    assert session.poll_target() is None
    assert not session.play("https://example.test/video", (0, 0), (640, 360))
    worker.shutdown.assert_called_once_with(wait=False, cancel_futures=True)
    player.play.assert_not_called()
    player.stop.assert_not_called()
