"""Embedded-map lifecycle, fallback, resizing and stale startup behavior."""
import threading
from unittest.mock import Mock
import pytest
from apps.orcUi.cesium_map_runtime import CesiumMapRuntime
from ui.navigation import GeoPoint, MapMarker, MapMarkerKind
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.map_platform_if import MapPlatform
from ui.navigation.poi_overlay_state import PoiOverlayState


@pytest.fixture
def mounted():
    native, viewer = Mock(), Mock()
    viewer.tick.return_value = True
    runtime = CesiumMapRuntime(native,viewer)
    runtime.resize(700,300,999)
    runtime.launch(100)
    yield runtime,native,viewer
    runtime.close()


def flush(runtime):
    runtime._worker.submit(lambda:None).result(timeout=3)


def explore(runtime):
    runtime.request_explore(CesiumViewerState(GeoPoint(.7,-1.4),label='Place'))
    flush(runtime)


def test_selected_place_is_embedded_and_switching_back_restores_native(mounted):
    runtime,native,viewer = mounted
    explore(runtime)
    assert runtime.state.active is MapPlatform.CESIUM
    assert runtime.state.available_platforms == (MapPlatform.MAPLIBRE,MapPlatform.CESIUM)
    state,host,size,current = viewer.open.call_args.args
    assert state.label == 'Place' and host == 100 and size == (700,300) and current()
    native.stop.assert_called_once()
    runtime.request_platform(MapPlatform.MAPLIBRE)
    flush(runtime)
    assert runtime.state.active is MapPlatform.MAPLIBRE
    native.launch.assert_called_with(100)


def test_return_button_restores_map_and_resizes_on_worker(mounted):
    runtime,native,viewer = mounted
    explore(runtime)
    runtime.resize(500,250,999)
    runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
    viewer.tick.assert_called_with((500,250))
    viewer.tick.return_value = False
    runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
    assert runtime.state.active is MapPlatform.MAPLIBRE
    native.launch.assert_called_with(100)


def test_startup_failure_is_visible_and_restores_native(mounted):
    runtime,native,viewer = mounted
    viewer.open.side_effect = RuntimeError('no xdotool')
    explore(runtime)
    assert not runtime.state.busy
    assert runtime.state.active is MapPlatform.MAPLIBRE
    assert 'no xdotool' in runtime.state.status
    native.launch.assert_called_with(100)


def test_stop_cancels_pending_startup_before_destroying_host(mounted):
    runtime,native,viewer = mounted
    entered,release = threading.Event(),threading.Event()
    cancelled=[]
    def opening(state,host,size,current):
        entered.set()
        assert release.wait(3)
        cancelled.append(not current())
    viewer.open.side_effect=opening
    runtime.request_platform(MapPlatform.CESIUM)
    assert entered.wait(3)
    stopped=threading.Event()
    thread=threading.Thread(target=lambda:(runtime.stop(),stopped.set()))
    thread.start()
    try:
        # A worker barrier ensures stop invalidated this generation before cleanup.
        for _ in range(100):
            if runtime._host is None:
                break
            threading.Event().wait(.001)
        release.set()
        assert stopped.wait(3)
        assert cancelled == [True]
        assert runtime.state.active is MapPlatform.MAPLIBRE
        assert runtime._host is None
    finally:
        release.set()
        thread.join(3)


def test_switch_during_startup_discards_stale_completion(mounted):
    runtime,native,viewer = mounted
    entered,release=threading.Event(),threading.Event()
    checks=[]
    def opening(state,host,size,current):
        entered.set()
        assert release.wait(3)
        checks.append(current())
    viewer.open.side_effect=opening
    runtime.request_platform(MapPlatform.CESIUM)
    assert entered.wait(3)
    runtime.request_platform(MapPlatform.MAPLIBRE)
    release.set()
    flush(runtime)
    assert checks == [False]
    assert runtime.state.active is MapPlatform.MAPLIBRE


def test_hidden_screen_rejects_exploration_and_close_is_idempotent(mounted):
    runtime,native,viewer=mounted
    runtime.stop()
    with pytest.raises(RuntimeError,match='Navigation'):
        runtime.request_explore(CesiumViewerState(GeoPoint(.7,-1.4)))
    runtime.close()
    runtime.close()


def test_x11_resize_failure_returns_to_native_with_visible_error(mounted):
    import subprocess
    runtime,native,viewer=mounted
    explore(runtime)
    viewer.tick.side_effect=subprocess.CalledProcessError(1,['xdotool','windowsize'])
    runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
    assert runtime.state.active is MapPlatform.MAPLIBRE
    assert 'xdotool' in runtime.state.status
    native.launch.assert_called_with(100)


def test_camera_requests_only_reach_current_exploration(mounted):
    from ui.navigation.map_platform_if import ExplorationCameraAction
    runtime,native,viewer = mounted
    runtime.request_camera(ExplorationCameraAction.PAN_UP)
    flush(runtime)
    viewer.request_camera.assert_not_called()
    explore(runtime)
    runtime.request_camera(ExplorationCameraAction.ZOOM_IN)
    flush(runtime)
    viewer.request_camera.assert_called_once_with(ExplorationCameraAction.ZOOM_IN)
    old_generation = runtime._generation
    runtime.request_platform(MapPlatform.MAPLIBRE)
    flush(runtime)
    runtime._camera(ExplorationCameraAction.PAN_UP, old_generation)
    assert viewer.request_camera.call_count == 1


def test_vehicle_follow_preserves_zoom_and_pauses_for_manual_camera(mounted):
    from ui.navigation.map_platform_if import ExplorationCameraAction
    runtime,native,viewer = mounted
    explore(runtime)
    point = GeoPoint(.7,-1.4)
    runtime.update_position(point)
    runtime.request_follow(True)
    runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
    viewer.update_position.assert_called_with(point,True)
    assert runtime.state.follow_enabled and runtime.state.position_available
    runtime.request_camera(ExplorationCameraAction.ZOOM_IN)
    flush(runtime)
    assert runtime.state.follow_enabled
    runtime.request_camera(ExplorationCameraAction.PAN_UP)
    flush(runtime)
    assert not runtime.state.follow_enabled
    runtime.request_camera(ExplorationCameraAction.RECENTER)
    flush(runtime)
    assert runtime.state.follow_enabled
    viewer.consume_manual_camera.return_value = True
    runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
    viewer.update_position.assert_called_with(point,False)
    assert not runtime.state.follow_enabled


def test_stale_fix_hides_vehicle_and_waits_without_using_cached_origin(mounted,monkeypatch):
    from apps.orcUi import cesium_map_runtime as module
    runtime,native,viewer = mounted
    explore(runtime)
    point = GeoPoint(.7,-1.4)
    now = [100.0]
    monkeypatch.setattr(module.time,'monotonic',lambda:now[0])
    runtime.update_position(point)
    runtime.request_follow(True)
    runtime._send_position(runtime._generation)
    viewer.update_position.assert_called_with(point,True)
    now[0] = 111.0
    runtime._send_position(runtime._generation)
    viewer.update_position.assert_called_with(None,True)
    assert not runtime.state.position_available
    assert 'Waiting' in runtime.state.status
    runtime.update_position(point)
    runtime._send_position(runtime._generation)
    viewer.update_position.assert_called_with(point,True)


def test_position_updates_are_coalesced_and_old_generation_cannot_follow(mounted):
    runtime,native,viewer = mounted
    explore(runtime)
    old_generation = runtime._generation
    for index in range(100):
        runtime.update_position(GeoPoint(.7,-1.4+index/10000))
    viewer.update_position.assert_not_called()
    runtime._send_position(old_generation)
    assert viewer.update_position.call_count == 1
    runtime.request_platform(MapPlatform.MAPLIBRE)
    flush(runtime)
    runtime._send_position(old_generation)
    assert viewer.update_position.call_count == 1


def test_poi_results_are_cached_and_sent_only_to_the_active_3d_view(mounted):
    runtime,native,viewer = mounted
    overlay = PoiOverlayState((MapMarker('fuel',GeoPoint(.7,-1.4),
                              MapMarkerKind.SEARCH_RESULT,'Fuel'),),'fuel')
    runtime.update_poi_overlay(overlay)
    flush(runtime)
    viewer.update_poi_overlay.assert_not_called()
    explore(runtime)
    viewer.update_poi_overlay.assert_called_once_with(overlay)
    replacement = PoiOverlayState((), '')
    runtime.update_poi_overlay(replacement)
    flush(runtime)
    viewer.update_poi_overlay.assert_called_with(replacement)


def test_one_browser_poll_timeout_keeps_terrain_and_success_resets_budget(mounted):
    runtime,native,viewer=mounted
    runtime._stop_tick.set()
    runtime._ticker.join(timeout=2)
    explore(runtime)
    viewer.close.reset_mock()
    viewer.tick.side_effect=[TimeoutError('timed out'),True,TimeoutError('timed out'),True]
    for _ in range(4):
        runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
        assert runtime.state.active is MapPlatform.CESIUM
    viewer.close.assert_not_called()
    assert runtime._poll_timeouts==0


def test_repeated_browser_poll_timeouts_restore_map_with_reason(mounted,caplog):
    runtime,native,viewer=mounted
    runtime._stop_tick.set()
    runtime._ticker.join(timeout=2)
    explore(runtime)
    viewer.tick.side_effect=TimeoutError('browser timed out')
    for _ in range(3):
        runtime._worker.submit(runtime._tick,runtime._generation).result(timeout=3)
    assert runtime.state.active is MapPlatform.MAPLIBRE
    assert 'browser timed out' in runtime.state.status
    assert '3D map returned to Map' in caplog.text
