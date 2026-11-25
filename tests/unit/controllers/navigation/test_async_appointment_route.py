# SPDX-License-Identifier: MIT
"""Regression coverage for asynchronous route initiation."""

from threading import Event, get_ident
from unittest.mock import Mock

import pytest

from controllers.navigation.navigation_route_request_handler import NavigationRouteRequestHandler
from ui.navigation import GeoPoint
from ui.navigation.route_types import TravelMode


@pytest.mark.parametrize("fails", [False, True])
def test_route_completion_is_collected_on_owner_thread(fails):
    entered = Event()
    release = Event()
    client = Mock()
    renderer = Mock()
    route = Mock()
    route.shape = (Mock(latitude=1.0, longitude=2.0),)
    route.operation_id = None
    owner = get_ident()
    observed = []

    def start(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        if fails:
            raise RuntimeError("route unavailable")
        return route

    client.start_route.side_effect = start
    handler = NavigationRouteRequestHandler(client, renderer)
    handler.observe_route(lambda result: observed.append((get_ident(), result)))
    try:
        handler.request_start_route_async(GeoPoint(0.1, 0.2), TravelMode.AUTO)
        assert entered.wait(5)
        assert handler.route_start_pending
        assert not handler.poll_route_start()
        with pytest.raises(RuntimeError):
            handler.request_cancel_route()
        with pytest.raises(RuntimeError):
            handler.request_start_route_async(GeoPoint(0.1, 0.2), TravelMode.AUTO)
        future = handler._pending
        assert future is not None
        release.set()
        if fails:
            with pytest.raises(RuntimeError, match="route unavailable"):
                future.result(timeout=5)
            with pytest.raises(RuntimeError, match="route unavailable"):
                handler.poll_route_start()
            assert not observed
        else:
            assert future.result(timeout=5) is route
            assert not observed
            assert handler.poll_route_start()
            assert observed == [(owner, route)]
        assert not handler.route_start_pending
    finally:
        release.set()
        handler.close()


def test_shutdown_discards_inflight_route_completion():
    entered = Event()
    release = Event()
    client = Mock()
    renderer = Mock()

    def start(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return Mock()

    client.start_route.side_effect = start
    handler = NavigationRouteRequestHandler(client, renderer)
    observer = Mock()
    handler.observe_route(observer)
    try:
        handler.request_start_route_async(GeoPoint(0.1, 0.2), TravelMode.AUTO)
        assert entered.wait(5)
        future = handler._pending
        assert future is not None
        handler.close()
        release.set()
        future.result(timeout=5)
        assert not handler.poll_route_start()
        assert not handler.route_start_pending
        observer.assert_not_called()
        renderer.set_route.assert_not_called()
        renderer.close.assert_called_once()
    finally:
        release.set()
