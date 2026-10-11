"""Embedded-map lifecycle, fallback, resizing and stale startup behavior."""
import threading
from unittest.mock import Mock
import pytest
from apps.orcUi.cesium_map_runtime import CesiumMapRuntime
from ui.navigation import GeoPoint
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.map_platform_if import MapPlatform


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
