from threading import Event
import time
from unittest.mock import Mock

import pytest

from apps.launchers import cesium_poi_actions as module
from ui.navigation import GeoPoint
from ui.navigation.poi_models import PointOfInterest, PoiCategory, PoiAction, PoiActionKind


@pytest.fixture
def native(monkeypatch, tmp_path):
    server, browser = Mock(), Mock()
    server.close_requested = Event()
    browser.is_running.return_value = True
    server.url = 'http://127.0.0.1:1234/'
    server_factory, browser_factory = Mock(return_value=server), Mock(return_value=browser)
    monkeypatch.setattr(module,'CesiumViewerServer',server_factory)
    monkeypatch.setattr(module,'BrowserKioskLauncher',browser_factory)
    for name in ('detroit_pack_directory','detroit_terrain_directory','detroit_building_directory'):
        monkeypatch.setattr(module,name,lambda: tmp_path/'absent')
    monkeypatch.setattr(module,'logging_file_path',lambda *args: tmp_path/'viewer.log')
    adapter = module.CesiumPoiActions(Mock())
    yield adapter, server, browser, server_factory, browser_factory
    adapter.close()


def poi():
    return PointOfInterest('place','Chosen place',PoiCategory.OTHER,GeoPoint(.7,-1.4))


def test_selected_destination_owned_profile_and_shutdown(native):
    adapter, server, browser, factory, browser_factory = native
    selected = poi()
    adapter.execute(selected, adapter.action_for(selected))
    state = factory.call_args.args[1]
    assert state.destination == selected.position
    assert state.label == selected.name
    assert 'orc-cesium-poi-' in browser_factory.call_args.kwargs['profile_path']
    with pytest.raises(RuntimeError,match='current 3D viewer'):
        adapter.execute(selected,adapter.action_for(selected))
    adapter.close()
    adapter.close()
    browser.stop.assert_called_once()
    server.close.assert_called_once()
    with pytest.raises(RuntimeError,match='closed'):
        adapter.execute(selected,adapter.action_for(selected))


def test_return_request_cleans_up_and_allows_next_destination(native):
    adapter, server, browser, _, _ = native
    adapter.execute(poi(),adapter.action_for(poi()))
    server.close_requested.set()
    deadline = time.monotonic()+2
    while not server.close.called and time.monotonic() < deadline:
        time.sleep(.02)
    assert server.close.called
    browser.stop.assert_called_once()
    server.close_requested.clear()
    adapter.execute(poi(),adapter.action_for(poi()))


def test_launch_failure_closes_all_resources(native):
    adapter, server, browser, _, _ = native
    browser.launch.side_effect = RuntimeError('Cannot start Chromium')
    with pytest.raises(RuntimeError,match='Cannot start'):
        adapter.execute(poi(),adapter.action_for(poi()))
    browser.stop.assert_called_once()
    server.close.assert_called_once()


def test_other_actions_delegate():
    fallback = Mock()
    adapter = module.CesiumPoiActions(fallback)
    action = PoiAction(PoiActionKind.OPEN_WEBSITE,'Website')
    assert adapter.execute(poi(),action) is fallback.execute.return_value
