# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Async lighting and Earth/POI diagnostics stay quiet, correlated and private."""

from concurrent.futures import Future
import logging
import sqlite3
import threading
from unittest.mock import AsyncMock, Mock, patch

import pytest

from common.logging.structured import operation
from common.logging.unit_test.test_device_logging import PRIVATE, records, wait_until
from controllers.lighting.adapters import leddmx_bluetooth_controller as ble
from controllers.lighting.lighting_presenter import LightingPresenter
from controllers.lighting.parsers.leddmx_config_parser import LedDmxBluetoothConfig
from controllers.navigation.earth_geolocation_bridge import EarthGeolocationBridge
from controllers.navigation.earth_navigation_controller import EarthNavigationController
from controllers.poi.navigation_places_controller import NavigationPlacesController
from controllers.poi.poi_search_controller import PoiSearchController
from ui.navigation import GeoPoint
from ui.navigation.poi_models import PoiAction, PoiActionKind, PoiCategory, PointOfInterest


def test_lighting_completion_errors_and_recovery_retain_request_ids(caplog):
    caplog.set_level(logging.DEBUG)
    backend, ui = Mock(), Mock()
    queued = []
    presenter = LightingPresenter(backend, ui, queued.append)
    futures = [Future() for _ in range(3)]
    backend.set_brightness.side_effect = futures
    for index, future in enumerate(futures):
        with operation(f"lighting-{index}"):
            presenter.request_brightness(27)
        if index < 2:
            future.set_exception(OSError(PRIVATE))
        else:
            # Refresh builds UI state; no backend values are serialized to logs.
            presenter.refresh = Mock()
            future.set_result(None)
        queued.pop(0)()
    emitted = records(caplog, "lighting.ui")
    failures = [r for r in emitted if r["event"] == "lighting.failed"]
    assert len(failures) == 1 and failures[0]["operation_id"] == "lighting-0"
    recovered = next(r for r in emitted if r["event"] == "lighting.recovered")
    assert recovered["operation_id"] == "lighting-2"


def test_bluetooth_write_retry_and_recovery_never_log_device_or_packets(caplog):
    caplog.set_level(logging.DEBUG)
    client = Mock()
    client.is_connected = False
    client.services = [PRIVATE]
    async def connect():
        client.is_connected = True
    async def disconnect():
        client.is_connected = False
    client.connect = AsyncMock(side_effect=connect)
    client.disconnect = AsyncMock(side_effect=disconnect)
    client.write_gatt_char = AsyncMock(side_effect=[OSError(PRIVATE), None])
    config = LedDmxBluetoothConfig("ffe0", "ffe1", (), (), False, 0, 0, 1, 1)
    with patch.object(ble, "BleakClient", return_value=client), patch.object(ble, "BleakScanner", Mock()), \
         patch.object(ble.LedDmxBluetoothController, "_client_has_leddmx_characteristic", return_value=True):
        # Drive the real coroutine on this thread: no socket wakeups/hardware needed.
        with patch.object(threading.Thread, "start"), patch.object(threading.Event, "wait", return_value=True):
            controller = ble.LedDmxBluetoothController(PRIVATE, config=config)
        try:
            pending = []
            future = Future()
            def schedule(coroutine, loop):
                pending.append(coroutine)
                return future
            with patch.object(ble.asyncio, "run_coroutine_threadsafe", side_effect=schedule):
                with operation("ble-command"):
                    assert controller.set_brightness(37) is future
            controller._loop.run_until_complete(pending.pop())
            assert controller.is_connected
        finally:
            controller._loop.run_until_complete(controller._disconnect())
            controller._loop.close()
    emitted = records(caplog, "lighting.bluetooth")
    failure = next(r for r in emitted if r["event"] == "lighting.failed")
    recovery = next(r for r in emitted if r["event"] == "lighting.recovered")
    assert failure["stage"] == recovery["stage"] == "write"
    assert failure["operation_id"] == recovery["operation_id"] == "ble-command"
    assert client.write_gatt_char.await_count == 2


def test_earth_bridge_retries_and_safe_trace_exclude_coordinates_and_endpoint(caplog, monkeypatch, capsys):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("ORC_EARTH_TRACE", "1")
    client = Mock()
    client.version.return_value = {"webSocketDebuggerUrl": PRIVATE}
    client.command.side_effect = [OSError(PRIVATE), OSError(PRIVATE), {}]
    client.evaluate_earth.return_value = True
    bridge = EarthGeolocationBridge(client)
    with operation("earth-request"):
        assert not bridge.install()
        assert not bridge.install()
        assert bridge.install()
        client.evaluate_earth.side_effect = [OSError(PRIVATE), 2, OSError(PRIVATE), 2, True]
        assert not bridge.push_position(42.8028, -83.0127)
        assert not bridge.push_position(42.8028, -83.0127)
        assert bridge.push_position(42.8028, -83.0127)
    emitted = records(caplog, "navigation.earth.bridge")
    assert len([r for r in emitted if r["event"] == "earth.failed" and r["stage"] == "install"]) == 1
    assert any(r["event"] == "earth.recovered" for r in emitted)
    assert all(r["operation_id"] == "earth-request" for r in emitted)
    assert capsys.readouterr().out == ""


def test_earth_waiting_states_are_logged_once_without_gps_payloads(caplog):
    caplog.set_level(logging.DEBUG)
    bridge, camera, dispatcher = Mock(), Mock(), Mock()
    controller = EarthNavigationController(bridge=bridge, camera=camera, dispatcher=dispatcher)
    bridge.install.return_value = False
    assert not controller.tick()
    assert not controller.tick()
    bridge.install.return_value = True
    assert not controller.tick()
    assert not controller.tick()
    emitted = records(caplog, "navigation.earth")
    transitions = [r for r in emitted if r["event"] == "earth.state_changed"]
    assert [r["state"] for r in transitions] == ["waiting_for_bridge", "waiting_for_fix"]
    assert all(r["level"] == "DEBUG" for r in emitted if r not in transitions)


def test_poi_database_failure_recovery_and_search_ids_exclude_names_paths_and_bounds(caplog):
    caplog.set_level(logging.DEBUG)
    source, database = Mock(), Mock()
    # Select the headless path rather than the renderer viewport transport.
    source.request_search = source.poll_search_result = None
    database.search.side_effect = [sqlite3.OperationalError(PRIVATE),
                                   sqlite3.OperationalError(PRIVATE), ()]
    controller = PoiSearchController(source, search_source=database,
                                     position_provider=lambda: GeoPoint(0.5, -1))
    for index in range(3):
        with operation(f"search-{index}"):
            controller.search(PoiCategory.FOOD)
    emitted = records(caplog, "navigation.poi")
    failure = [r for r in emitted if r["event"] == "poi.failed"]
    assert len(failure) == 1 and failure[0]["operation_id"] == "search-0"
    recovery = next(r for r in emitted if r["event"] == "poi.recovered")
    assert recovery["operation_id"] == "search-2"


def test_place_action_worker_carries_operation_and_discards_result_after_close(caplog):
    caplog.set_level(logging.DEBUG)
    entered, release = threading.Event(), threading.Event()
    def execute(*args):
        entered.set()
        assert release.wait(2)
        return PRIVATE
    executor = Mock(execute=execute)
    controller = NavigationPlacesController(Mock(), Mock(), executor)
    poi = PointOfInterest(PRIVATE, PRIVATE, PoiCategory.FOOD, GeoPoint(0.5, -1))
    action = PoiAction(PoiActionKind.OPEN_WEBSITE, PRIVATE, uri=PRIVATE)
    with operation("place-request"):
        assert controller.request_action(poi, action) == 1
    assert entered.wait(1)
    controller.close()
    release.set()
    wait_until(lambda: not controller._action_pending)
    assert controller.poll_action_result() is None
    emitted = records(caplog, "navigation.poi.actions")
    assert any(r["event"] == "poi.result_discarded" for r in emitted)
    assert all(r["operation_id"] == "place-request" for r in emitted)


def test_place_worker_start_failure_releases_pending_action(caplog):
    caplog.set_level(logging.DEBUG)
    controller = NavigationPlacesController(Mock(), Mock(), Mock())
    with patch("controllers.poi.navigation_places_controller.threading.Thread.start",
               side_effect=OSError(PRIVATE)), pytest.raises(OSError):
        controller.request_action(Mock(), Mock())
    assert not controller._action_pending
    assert any(r.get("stage") == "worker_start" for r in records(caplog, "navigation.poi.actions"))
