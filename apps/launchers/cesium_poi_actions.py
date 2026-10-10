"""Owned native adapter for offline, destination-only 3D exploration."""
from contextlib import ExitStack
import os
import re
from tempfile import TemporaryDirectory
import threading

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.cesium_sdk import sdk_directory
from apps.launchers.cesium_viewer_server import CesiumViewerServer
from apps.launchers.local_imagery_pack import LocalImageryPack, detroit_pack_directory
from apps.launchers.local_terrain_pack import load_terrain, preferred_terrain_directory
from apps.launchers.local_building_pack import load_buildings, detroit_building_directory
from apps.launchers.local_map_tiles_pack import load_viewer_tiles, preferred_tiles_directory
from common.logging.logging_paths import logging_file_path
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from ui.navigation.cesium_viewer_state import CesiumViewerState
from ui.navigation.poi_models import PoiAction, PoiActionKind


class CesiumPoiActions(PoiActionExecutorIf):
    """Own one viewer at a time; composition closes it on application shutdown."""

    def __init__(self, fallback):
        self._fallback = fallback
        self._lock = threading.RLock()
        self._session = None
        self._closed = False

    def action_for(self, poi):
        return PoiAction(PoiActionKind.EXPLORE_3D, 'Explore offline 3D map',
                         provider_id='local-3d')

    def execute(self, poi, action):
        if action.kind is not PoiActionKind.EXPLORE_3D:
            return self._fallback.execute(poi, action)
        if action.provider_id != 'local-3d':
            raise ValueError('Invalid local 3D action')
        state = CesiumViewerState(poi.position, label=poi.name[:120] or 'Selected place')
        with self._lock:
            if self._closed:
                raise RuntimeError('3D viewer adapter is closed')
            if self._session is not None:
                raise RuntimeError('Close the current 3D viewer before opening another place')
            imagery_dir, terrain_dir, building_dir = (detroit_pack_directory(),
                                                     preferred_terrain_directory(), detroit_building_directory())
            tile_dir = preferred_tiles_directory()
            tiles = load_viewer_tiles(tile_dir) if tile_dir.exists() else None
            imagery = LocalImageryPack.load(imagery_dir) if (tiles is None or not any(t.imagery_available for t in tiles.state.tiles)) and imagery_dir.exists() else None
            terrain = load_terrain(terrain_dir) if terrain_dir.exists() else None
            buildings = load_buildings(building_dir) if tiles is None and building_dir.exists() else None
            display = os.environ.get('DISPLAY', ':1')
            resources = ExitStack()
            try:
                server = CesiumViewerServer(sdk_directory(), state, imagery=imagery,
                                             terrain=terrain, buildings=buildings, tiles=tiles)
                resources.callback(server.close)
                profile = resources.enter_context(TemporaryDirectory(prefix='orc-cesium-poi-'))
                browser = BrowserKioskLauncher(url=server.url, profile_path=profile,
                    process_pattern=re.escape(profile), kiosk=False, app_mode=True,
                    startup_grace_seconds=.5, extra_arguments=('--start-maximized',),
                    log_file=logging_file_path('openroadcode','cesium-viewer.log'))
                resources.callback(browser.stop, display, None)
                server.start()
                browser.launch(display, None)
                stop = threading.Event()
                session = (resources, server, browser, stop)
                self._session = session
                threading.Thread(target=self._watch, args=(session,),
                                 name='orc-cesium-poi', daemon=True).start()
            except Exception:
                self._session = None
                resources.close()
                raise
        return 'Opened offline 3D map; use Return to ORC to close'

    def _watch(self, session):
        _, server, browser, stop = session
        try:
            while not stop.wait(.2):
                if server.close_requested.is_set() or not browser.is_running():
                    break
        finally:
            with self._lock:
                if self._session is session:
                    self._session = None
                    session[0].close()

    def close(self):
        with self._lock:
            self._closed = True
            session, self._session = self._session, None
            if session is not None:
                session[3].set()
                session[0].close()
