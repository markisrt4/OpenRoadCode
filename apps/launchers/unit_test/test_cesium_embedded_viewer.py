"""Attach a blank browser before WebGL navigation and own cleanup on every path."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from apps.launchers import cesium_embedded_viewer as module
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState


@pytest.fixture
def native(tmp_path,monkeypatch):
    events=[]
    absent=tmp_path/'absent'
    for name in ('preferred_imagery_directory','preferred_terrain_directory','detroit_building_directory','preferred_tiles_directory'):
        monkeypatch.setattr(module,name,lambda *args:absent)
    monkeypatch.setattr(module,'sdk_directory',lambda:tmp_path/'sdk')
    monkeypatch.setattr(module,'logging_file_path',lambda *args:tmp_path/'embedded.log')
    browser=Mock()
    browser.is_running.return_value=True
    server=Mock(url='http://127.0.0.1:12345/')
    server.close_requested.is_set.return_value=False
    server.close.side_effect=lambda:events.append('server.close')
    browser.stop.side_effect=lambda *args:events.append('browser.stop')
    servers=Mock(return_value=server)
    monkeypatch.setattr(module,'CesiumViewerServer',servers)
    def make_browser(**kwargs):
        assert kwargs['url']=='about:blank'
        (Path(kwargs['profile_path'])/'DevToolsActivePort').write_text('54321\n/path\n')
        events.append('browser.blank')
        return browser
    browsers=Mock(side_effect=make_browser)
    monkeypatch.setattr(module,'BrowserKioskLauncher',browsers)
    devtools=Mock()
    devtools.targets.return_value=[SimpleNamespace(url='about:blank')]
    devtools.command.side_effect=lambda *args:events.append('page.navigate') or {}
    monkeypatch.setattr(module,'ChromiumDevToolsClient',Mock(return_value=devtools))
    embedder=Mock()
    embedder.supported.return_value=True
    embedder.embed.side_effect=lambda *args,**kwargs:events.append('window.embed')
    viewer=module.CesiumEmbeddedViewer(embedder=embedder)
    yield SimpleNamespace(viewer=viewer,browser=browser,server=server,servers=servers,
        browsers=browsers,embedder=embedder,devtools=devtools,events=events)
    viewer.close()


def state():
    return CesiumViewerState(GeoPoint(.7,-1.4),label='Place')


def test_blank_window_is_attached_before_webgl_load_and_closed_before_http_origin(native):
    native.viewer.open(state(),100,(640,320))
    assert native.servers.call_args.args[1].embedded is True
    assert native.events.index('window.embed')<native.events.index('page.navigate')
    native.devtools.command.assert_called_once_with(native.devtools.targets.return_value[0],
        'Page.navigate',{'url':native.server.url})
    profile=Path(native.browsers.call_args.kwargs['profile_path'])
    assert profile.exists()
    assert native.viewer.tick((500,300))
    native.embedder.resize.assert_called_once_with(500,300)
    native.server.close_requested.is_set.return_value=True
    assert not native.viewer.tick((500,300))
    native.viewer.close()
    assert not profile.exists()
    assert native.events.index('browser.stop')<native.events.index('server.close')
    native.viewer.close()
    native.browser.stop.assert_called_once()


def test_cancel_after_attachment_does_not_navigate_and_releases_owned_resources(native):
    cancelled=False
    def attach(*args,**kwargs):
        nonlocal cancelled
        cancelled=True
    native.embedder.embed.side_effect=attach
    native.viewer.open(state(),100,(640,320),lambda:not cancelled)
    native.devtools.command.assert_not_called()
    native.browser.stop.assert_called_once()
    native.server.close.assert_called_once()
    assert not Path(native.browsers.call_args.kwargs['profile_path']).exists()


def test_navigation_failure_cleans_up_browser_profile_and_server(native):
    native.devtools.command.side_effect=RuntimeError('CDP failed')
    with pytest.raises(RuntimeError,match='CDP failed'):
        native.viewer.open(state(),100,(640,320))
    native.browser.stop.assert_called_once()
    native.server.close.assert_called_once()
    assert not Path(native.browsers.call_args.kwargs['profile_path']).exists()


def test_missing_embedding_tool_fails_before_browser_launch(native):
    native.embedder.supported.return_value=False
    with pytest.raises(RuntimeError,match='xdotool'):
        native.viewer.open(state(),100,(640,320))
    native.browsers.assert_not_called()
