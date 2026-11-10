# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from threading import Event
from unittest.mock import Mock, patch

from frontends.x11.waydroid_window_embedder import WaydroidWindowEmbedder


def test_stalled_android_output_is_nudged_then_restored_and_acknowledged():
    embedder = WaydroidWindowEmbedder()
    embedder._window_id = 42
    cancelled = Mock()
    cancelled.wait.return_value = False
    cancelled.is_set.return_value = False
    with patch.object(embedder, '_android_size', side_effect=[(567, 586), (1132, 586)]), \
            patch('frontends.x11.x11_window_embedder.X11WindowEmbedder.resize') as resize:
        embedder._settle(cancelled, (1132, 538), (0, 48))
    assert [call.args for call in resize.call_args_list] == [(1130, 538), (1132, 538)]


def test_acknowledged_or_unavailable_output_does_not_nudge():
    for actual in ((566, 586), None):
        embedder = WaydroidWindowEmbedder()
        cancelled = Mock()
        cancelled.wait.return_value = False
        with patch.object(embedder, '_android_size', return_value=actual), \
                patch('frontends.x11.x11_window_embedder.X11WindowEmbedder.resize') as resize:
            embedder._settle(cancelled, (566, 538), (0, 48))
        resize.assert_not_called()


def test_new_resize_and_clear_cancel_old_workers():
    embedder = WaydroidWindowEmbedder()
    embedder._window_id = 42
    first = embedder._resize_cancel
    with patch('apps.orcUi.adapters.waydroid_window_embedder.Thread'), \
            patch('frontends.x11.x11_window_embedder.X11WindowEmbedder.resize'):
        embedder.resize(566, 538)
        second = embedder._resize_cancel
        assert first.is_set()
        assert not second.is_set()
        embedder.resize(1132, 538)
        assert second.is_set()
        third = embedder._resize_cancel
        embedder.clear()
        assert third.is_set()
        assert embedder.window_id is None


def test_cancelled_worker_never_touches_detached_window():
    embedder = WaydroidWindowEmbedder()
    cancelled = Event()
    cancelled.set()
    with patch.object(embedder, '_android_size') as size, \
            patch('frontends.x11.x11_window_embedder.X11WindowEmbedder.resize') as resize:
        embedder._settle(cancelled, (1132, 538), (0, 48))
    size.assert_not_called()
    resize.assert_not_called()


def test_retry_is_bounded_when_android_never_acknowledges():
    embedder = WaydroidWindowEmbedder()
    embedder._window_id = 42
    cancelled = Mock()
    cancelled.wait.return_value = False
    cancelled.is_set.return_value = False
    with patch.object(embedder, '_android_size', return_value=(567, 586)), \
            patch('frontends.x11.x11_window_embedder.X11WindowEmbedder.resize') as resize:
        embedder._settle(cancelled, (1132, 538), (0, 48))
    assert resize.call_count == 6
    assert resize.call_args.args == (1132, 538)


def test_hide_during_property_query_cannot_resize_the_old_surface():
    embedder = WaydroidWindowEmbedder()
    embedder._window_id = 42
    cancelled = Mock()
    cancelled.wait.return_value = False

    def query_then_hide():
        embedder.clear()
        cancelled.is_set.return_value = True
        return (567, 586)

    with patch.object(embedder, '_android_size', side_effect=query_then_hide), \
            patch('frontends.x11.x11_window_embedder.X11WindowEmbedder.resize') as resize:
        embedder._settle(cancelled, (1132, 538), (0, 48))
    resize.assert_not_called()


def test_legacy_import_preserves_the_application_adapter_type():
    from apps.orcUi.adapters.waydroid_window_embedder import WaydroidWindowEmbedder as Adapter
    assert WaydroidWindowEmbedder is Adapter
