"""Own a local Cesium browser surface hosted in an ORC X11 map window."""

from contextlib import ExitStack
from dataclasses import replace
import os
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import time
import uuid

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.cesium_sdk import sdk_directory
from apps.launchers.cesium_viewer_server import CesiumViewerServer
from apps.launchers.local_imagery_pack import LocalImageryPack, detroit_pack_directory, preferred_imagery_directory
from apps.launchers.local_terrain_pack import load_terrain, preferred_terrain_directory
from apps.launchers.local_building_pack import load_buildings, detroit_building_directory
from apps.launchers.local_map_tiles_pack import load_viewer_tiles, preferred_tiles_directory
from common.logging.logging_paths import logging_file_path
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient


class CesiumEmbeddedViewer:
    """Worker-owned browser, local HTTP origin, profile and native surface."""

    def __init__(self, *, embedder=None):
        self._embedder = embedder or X11WindowEmbedder(timeout_seconds=.5)
        self._resources = None
        self._browser = None
        self._server = None
        self._size = None

    def open(self, state, parent_window_id, size, current=lambda: True):
        self.close()
        if not self._embedder.supported():
            raise RuntimeError('xdotool is required for the embedded 3D map')
        if not current():
            return
        imagery_dir = preferred_imagery_directory(state.destination)
        terrain_dir = preferred_terrain_directory(state.destination)
        building_dir = detroit_building_directory()
        tile_dir = preferred_tiles_directory()
        tiles = load_viewer_tiles(tile_dir) if tile_dir.exists() and imagery_dir == detroit_pack_directory() else None
        imagery = LocalImageryPack.load(imagery_dir) if imagery_dir.exists() and (tiles is None or not any(t.imagery_available for t in tiles.state.tiles)) else None
        terrain = load_terrain(terrain_dir) if terrain_dir.exists() else None
        buildings = load_buildings(building_dir) if tiles is None and building_dir.exists() else None
        display = os.environ.get('DISPLAY', ':1')
        resources = ExitStack()
        try:
            server = CesiumViewerServer(sdk_directory(), replace(state, embedded=True),
                                       imagery=imagery, terrain=terrain, buildings=buildings, tiles=tiles)
            resources.callback(server.close)
            profile = resources.enter_context(TemporaryDirectory(prefix='orc-cesium-embedded-'))
            window_class = 'orc-cesium-'+uuid.uuid4().hex
            startup_url = server.url+'embedded-start.html'
            browser = BrowserKioskLauncher(url=startup_url, profile_path=profile,
                process_pattern=re.escape(profile), kiosk=False, app_mode=True,
                window_position=(-20000,-20000), window_size=size,
                window_class=window_class, startup_grace_seconds=.2,
                extra_arguments=('--no-first-run','--no-default-browser-check',
                    '--remote-debugging-port=0','--remote-debugging-address=127.0.0.1'),
                log_file=logging_file_path('openroadcode','cesium-embedded.log'))
            resources.callback(browser.stop, display, None)
            server.start()
            if not current():
                resources.close()
                return
            browser.launch(display, None)
            deadline = time.monotonic()+10
            while current() and time.monotonic()<deadline:
                if not browser.is_running():
                    raise RuntimeError('Embedded Chromium exited during startup')
                try:
                    self._embedder.embed(0,parent_window_id,*size,window_class=window_class,relax_size_hints=True)
                    break
                except RuntimeError:
                    time.sleep(.05)
            else:
                if current():
                    raise RuntimeError('Timed out attaching Chromium to the map area')
                resources.close()
                self._embedder.clear()
                return
            # Navigate only after attachment: no live WebGL surface is reparented.
            deadline = time.monotonic()+10
            last_status = 'waiting for Chromium DevToolsActivePort'
            port_file = Path(profile)/'DevToolsActivePort'
            while current() and time.monotonic()<deadline:
                try:
                    port = int(port_file.read_text().splitlines()[0])
                    last_status = 'waiting for the local Chromium startup page'
                    devtools = ChromiumDevToolsClient(port=port)
                    target = next((item for item in devtools.targets() if item.url == startup_url), None)
                    if target is not None:
                        result = devtools.command(target,'Page.navigate',{'url':server.url})
                        if result.get('errorText'):
                            raise RuntimeError(result['errorText'])
                        break
                except (OSError, ValueError, IndexError) as error:
                    last_status = str(error)
                time.sleep(.05)
            else:
                if current():
                    raise RuntimeError(f'Timed out loading the embedded 3D map: {last_status}')
                resources.close()
                self._embedder.clear()
                return
            if not current():
                resources.close()
                self._embedder.clear()
                return
            self._resources, self._server, self._browser = resources, server, browser
            self._size = size
        except Exception:
            try:
                resources.close()
            finally:
                self._embedder.clear()
            raise

    def tick(self, size):
        if self._server is None or self._browser is None:
            raise RuntimeError('Embedded 3D map is not running')
        if self._server.close_requested.is_set():
            return False
        if not self._browser.is_running():
            raise RuntimeError('Embedded Chromium exited')
        if size != self._size:
            self._embedder.resize(*size)
            self._size = size
        return True

    def close(self):
        resources, self._resources = self._resources, None
        self._browser = self._server = self._size = None
        try:
            if resources is not None:
                # Close the browser while attached, before the Tk host is destroyed.
                resources.close()
        finally:
            self._embedder.clear()
