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
        assert kwargs['url']==server.url+'embedded-start.html'
        assert '--no-first-run' in kwargs['extra_arguments']
        assert '--no-default-browser-check' in kwargs['extra_arguments']
        (Path(kwargs['profile_path'])/'DevToolsActivePort').write_text('54321\n/path\n')
        events.append('browser.blank')
        return browser
    browsers=Mock(side_effect=make_browser)
    monkeypatch.setattr(module,'BrowserKioskLauncher',browsers)
    devtools=Mock()
    devtools.targets.return_value=[SimpleNamespace(url=server.url+'embedded-start.html')]
    def command(*args):
        if args[1] == 'Page.navigate':
            events.append('page.navigate')
            return {}
        return {'result': {'value': {'ready': True}}}
    devtools.command.side_effect = command
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
    native.devtools.command.assert_any_call(native.devtools.targets.return_value[0],
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


def test_loading_has_its_own_deadline_after_slow_x11_attachment(native,monkeypatch):
    # Window attachment consumes the original startup budget. Navigation must
    # still get its own budget rather than timing out before consulting DevTools.
    monkeypatch.setattr(module.time,'monotonic',Mock(side_effect=[0,0,20,20,21,21]))
    native.viewer.open(state(),100,(640,320))
    assert native.devtools.command.call_count == 2


def test_render_error_releases_owned_surface(native):
    native.devtools.command.side_effect = lambda target,method,params: (
        {} if method == 'Page.navigate' else {'result':{'value':{'ready':False,'error':'WebGL unavailable'}}})
    with pytest.raises(RuntimeError, match='WebGL unavailable'):
        native.viewer.open(state(),100,(640,320))
    native.browser.stop.assert_called_once()
    native.server.close.assert_called_once()


def test_camera_requests_validate_actions_before_browser_commands(native):
    from ui.navigation.map_platform_if import ExplorationCameraAction
    native.viewer.open(state(),100,(640,320))
    native.devtools.command.return_value = {'result':{'value':True}}
    native.devtools.command.side_effect = None
    native.viewer.request_camera(ExplorationCameraAction.PAN_UP)
    assert '"pan-up"' in native.devtools.command.call_args.args[2]['expression']
    with pytest.raises(ValueError):
        native.viewer.request_camera('arbitrary JS')


def test_startup_waits_for_rendered_frame_before_exposing_session(native, monkeypatch):
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    polls = []
    def command(target, method, parameters):
        if method == 'Page.navigate':
            return {}
        assert native.viewer._server is None
        polls.append(True)
        return {'result':{'value':{'ready':len(polls) > 1}}}
    native.devtools.command.side_effect = command
    native.viewer.open(state(),100,(640,320))
    assert len(polls) == 2
    assert native.viewer._server is native.server


def test_cancellation_while_waiting_for_frame_closes_surface(native, monkeypatch):
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    cancelled = False
    def command(target, method, parameters):
        nonlocal cancelled
        if method == 'Runtime.evaluate':
            cancelled = True
        return {'result':{'value':{'ready':False}}}
    native.devtools.command.side_effect = command
    native.viewer.open(state(),100,(640,320),lambda:not cancelled)
    native.browser.stop.assert_called_once()
    assert native.viewer._server is None
