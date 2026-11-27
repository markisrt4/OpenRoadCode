"""Own a local Cesium browser surface hosted in an ORC X11 map window."""

import json
import os
import re
import subprocess
import time
import uuid
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.launchers.browser_launcher import BrowserKioskLauncher
from apps.launchers.cesium_sdk import sdk_directory
from apps.launchers.cesium_viewer_server import CesiumViewerServer
from apps.launchers.local_building_pack import detroit_building_directory, load_buildings
from apps.launchers.local_imagery_pack import (
    LocalImageryPack,
    detroit_pack_directory,
    load_imagery_stack,
    preferred_imagery_directory,
)
from apps.launchers.local_imagery_pyramid import installed_imagery_pyramids
from apps.launchers.local_map_tiles_pack import load_viewer_tiles, preferred_tiles_directory
from apps.launchers.local_road_overlay import LocalRoadOverlay
from apps.launchers.local_terrain_pack import load_installed_terrain_catalog
from apps.launchers.state_boundary_overlay import load_state_boundary_overlay
from common.logging.logging_paths import logging_file_path
from frontends.x11.x11_window_embedder import X11WindowEmbedder
from protocols.chromium.chromium_devtools_client import ChromiumDevToolsClient
from ui.navigation import GeoPoint
from ui.navigation.map_layer_controls import MapLayerAction, MapLayerControl, MapLayerControls
from ui.navigation.map_platform_if import ExplorationCameraAction
from ui.navigation.poi_overlay_state import PoiOverlayState
from ui.navigation.route_overlay_state import RouteOverlayState


def _diagnostic(stage, **details):
    """Append and flush launch evidence before advancing a potentially fatal stage."""
    try:
        with logging_file_path("openroadcode", "cesium-stages.log").open(
            "a", encoding="utf-8"
        ) as log:
            log.write(json.dumps({"time": time.time(), "stage": stage, **details}) + "\n")
            log.flush()
    except (OSError, TypeError, ValueError):
        pass  # Diagnostic storage must not prevent rendering or cleanup.


def _rendering_arguments():
    """Opt-in diagnostic path; retain the default graphics backend otherwise."""
    mode = os.environ.get("OPENROAD_CESIUM_RENDERER", "default")
    if mode == "default":
        return ()
    if mode == "hardware-override":
        return ("--ignore-gpu-blocklist",)
    if mode == "software":
        return (
            "--use-gl=angle",
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--disable-gpu-compositing",
            "--disable-features=Vulkan",
        )
    raise ValueError("OPENROAD_CESIUM_RENDERER must be default, hardware-override or software")


class CesiumEmbeddedViewer:
    """Worker-owned browser, local HTTP origin, profile and native surface."""

    def __init__(self, *, embedder=None):
        self._embedder = embedder or X11WindowEmbedder(timeout_seconds=0.5)
        self._resources = None
        self._browser = None
        self._server = None
        self._size = None
        self._devtools = self._target = None
        self.layer_controls = MapLayerControls()
        self._manual_revision = 0
        self._manual_pending = False
        self._poi_selection = None

    def open(self, state, parent_window_id, size, current=lambda: True):
        self.close()
        _diagnostic(
            "launch-request",
            renderer=os.environ.get("OPENROAD_CESIUM_RENDERER", "default"),
            flags=_rendering_arguments(),
            size=size,
        )
        if not self._embedder.supported():
            raise RuntimeError("xdotool is required for the embedded 3D map")
        if not current():
            return
        _diagnostic("imagery-catalog-start")
        imagery_layers = load_imagery_stack()
        imagery_dir = (
            detroit_pack_directory()
            if imagery_layers
            else preferred_imagery_directory(state.destination)
        )
        building_dir = detroit_building_directory()
        tile_dir = preferred_tiles_directory(state.destination)
        tiles = load_viewer_tiles(tile_dir) if tile_dir.exists() else None
        imagery = (
            LocalImageryPack.load(imagery_dir)
            if not imagery_layers
            and imagery_dir.exists()
            and (tiles is None or not any(t.imagery_available for t in tiles.state.tiles))
            else None
        )
        _diagnostic("terrain-catalog-start")
        terrain = load_installed_terrain_catalog()
        _diagnostic("terrain-catalog-ready")
        buildings = (
            load_buildings(building_dir) if tiles is None and building_dir.exists() else None
        )
        _diagnostic("buildings-ready")
        roads = LocalRoadOverlay.installed()
        _diagnostic(
            "datasets-ready",
            latitude=state.destination.latitude_rad,
            longitude=state.destination.longitude_rad,
            distance_m=state.distance_m,
        )
        display = os.environ.get("DISPLAY", ":1")
        resources = ExitStack()
        try:
            server = CesiumViewerServer(
                sdk_directory(),
                replace(state, embedded=True),
                imagery=imagery,
                imagery_layers=imagery_layers,
                imagery_pyramids=installed_imagery_pyramids(),
                terrain=terrain,
                buildings=buildings,
                tiles=tiles,
                roads=roads,
                boundaries=load_state_boundary_overlay(),
            )
            resources.callback(server.close)
            profile = resources.enter_context(TemporaryDirectory(prefix="orc-cesium-embedded-"))
            window_class = "orc-cesium-" + uuid.uuid4().hex
            startup_url = server.url + "embedded-start.html"
            browser = BrowserKioskLauncher(
                url=startup_url,
                profile_path=profile,
                process_pattern=re.escape(profile),
                kiosk=False,
                app_mode=True,
                window_position=(-20000, -20000),
                window_size=size,
                window_class=window_class,
                startup_grace_seconds=0.2,
                extra_arguments=(
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--remote-debugging-port=0",
                    "--remote-debugging-address=127.0.0.1",
                )
                + _rendering_arguments(),
                log_file=logging_file_path("openroadcode", "cesium-embedded.log"),
            )
            resources.callback(browser.stop, display, None, owned_process_only=True)
            server.start()
            if not current():
                resources.close()
                return
            _diagnostic("browser-launch")
            browser.launch(display, None)
            deadline = time.monotonic() + 10
            while current() and time.monotonic() < deadline:
                if not browser.is_running():
                    raise RuntimeError("Embedded Chromium exited during startup")
                try:
                    self._embedder.embed(
                        0, parent_window_id, *size, window_class=window_class, relax_size_hints=True
                    )
                    break
                except RuntimeError:
                    time.sleep(0.05)
            else:
                if current():
                    raise RuntimeError("Timed out attaching Chromium to the map area")
                resources.close()
                self._embedder.clear()
                return
            _diagnostic("window-attached")
            # Navigate only after attachment: no live WebGL surface is reparented.
            deadline = time.monotonic() + 10
            last_status = "waiting for Chromium DevToolsActivePort"
            port_file = Path(profile) / "DevToolsActivePort"
            while current() and time.monotonic() < deadline:
                try:
                    port = int(port_file.read_text().splitlines()[0])
                    last_status = "waiting for the local Chromium startup page"
                    devtools = ChromiumDevToolsClient(port=port)
                    target = next(
                        (item for item in devtools.targets() if item.url == startup_url), None
                    )
                    if target is not None:
                        _diagnostic("graphics-info-request")
                        try:
                            info = devtools.system_info()
                            gpu = info.get("gpu", {})
                            _diagnostic("graphics-info", gpu=gpu)
                        except (OSError, RuntimeError, ValueError) as error:
                            _diagnostic("graphics-info-unavailable", error=str(error))
                        _diagnostic("terrain-navigation")
                        result = devtools.command(target, "Page.navigate", {"url": server.url})
                        if result.get("errorText"):
                            raise RuntimeError(result["errorText"])
                        break
                except (OSError, ValueError, IndexError) as error:
                    last_status = str(error)
                time.sleep(0.05)
            else:
                if current():
                    raise RuntimeError(f"Timed out loading the embedded 3D map: {last_status}")
                resources.close()
                self._embedder.clear()
                return
            last_stage = None
            _diagnostic("waiting-first-frame")
            deadline = time.monotonic() + 45
            while current() and time.monotonic() < deadline:
                if not browser.is_running():
                    raise RuntimeError("Embedded Chromium exited while rendering the map")
                try:
                    result = devtools.command(
                        target,
                        "Runtime.evaluate",
                        {
                            "expression": "({ready: window.ORCViewerReady === true, error: window.ORCViewerError || null, stage: window.ORCViewerStage || null})",
                            "returnByValue": True,
                        },
                    )
                except (OSError, RuntimeError):
                    # Navigation can briefly destroy the execution context.
                    time.sleep(0.1)
                    continue
                observed = result.get("result", {}).get("value", {})
                if observed.get("stage") != last_stage:
                    last_stage = observed.get("stage")
                    _diagnostic("page-stage", value=last_stage)
                if observed.get("error"):
                    raise RuntimeError(f"3D rendering failed: {observed['error']}")
                if observed.get("ready"):
                    _diagnostic("first-frame-ready")
                    break
                time.sleep(0.1)
            else:
                if current():
                    raise RuntimeError(
                        f"Timed out waiting for the first 3D map frame (stage: {last_stage or 'unknown'})"
                    )
            if not current():
                resources.close()
                self._embedder.clear()
                return
            self._resources, self._server, self._browser = resources, server, browser
            self._size = size
            self._devtools, self._target = devtools, target
        except Exception as error:
            _diagnostic("startup-failed", error=str(error))
            try:
                resources.close()
            finally:
                self._embedder.clear()
            raise

    def suspend(self):
        """Keep the owned browser and host association while Road map is visible."""
        self._set_visible(False)
        _diagnostic("viewer-retained")

    def resume(self, size):
        """Map the existing X11 child without reparenting its live WebGL surface."""
        if self._browser is None or not self._browser.is_running():
            raise RuntimeError("Retained Chromium exited")
        if self._server.close_requested.is_set():
            raise RuntimeError("Retained 3D viewer was closed")
        self._embedder.resize(*size)
        self._set_visible(True)
        self._size = size
        if not self.tick(size):
            raise RuntimeError("Retained 3D viewer requested close")
        _diagnostic("viewer-resumed")

    def _set_visible(self, visible):
        window_id = self._embedder.window_id
        if type(window_id) is not int or window_id <= 0:
            raise RuntimeError("Retained 3D window is unavailable")
        try:
            subprocess.run(
                ["xdotool", "windowmap" if visible else "windowunmap", str(window_id)],
                check=True,
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise RuntimeError("Could not change retained 3D window visibility") from error

    def request_camera(self, action):
        action = ExplorationCameraAction(action)
        if self._devtools is None:
            raise RuntimeError("3D camera is not ready")
        result = self._devtools.command(
            self._target,
            "Runtime.evaluate",
            {
                "expression": f"window.ORCExplorationCamera({json.dumps(action.value)})",
                "returnByValue": True,
            },
        )
        if result.get("exceptionDetails") or result.get("result", {}).get("value") is not True:
            raise RuntimeError("3D camera rejected the requested action")

    def request_layer(self, action):
        action = MapLayerAction(action)
        if self._devtools is None:
            raise RuntimeError("3D layers are not ready")
        result = self._devtools.command(
            self._target,
            "Runtime.evaluate",
            {
                "expression": f"window.ORCMapLayerAction({json.dumps(action.value)})",
                "returnByValue": True,
            },
        )
        if result.get("exceptionDetails") or result.get("result", {}).get("value") is not True:
            raise RuntimeError("Map layer unavailable")

    def tick(self, size):
        if self._server is None or self._browser is None:
            raise RuntimeError("Embedded 3D map is not running")
        if self._server.close_requested.is_set():
            return False
        if not self._browser.is_running():
            raise RuntimeError("Embedded Chromium exited")
        if size != self._size:
            self._embedder.resize(*size)
            self._size = size
        result = self._devtools.command(
            self._target,
            "Runtime.evaluate",
            {
                "expression": "({revision:window.ORCManualCameraRevision||0,poi:window.ORCConsumePoiSelection?window.ORCConsumePoiSelection():null,controls:window.ORCMapLayerState?window.ORCMapLayerState():[]})",
                "returnByValue": True,
            },
        )
        value = result.get("result", {}).get("value", {})
        self.layer_controls = MapLayerControls(
            tuple(
                MapLayerControl(
                    MapLayerAction(item["action"]),
                    str(item["label"])[:40],
                    item["available"] is True,
                    item["enabled"] is True,
                )
                for item in value.get("controls", [])
            )
        )
        revision = value.get("revision", 0)
        if type(revision) is int and revision != self._manual_revision:
            self._manual_pending = True
            self._manual_revision = revision
        marker_id = value.get("poi")
        if isinstance(marker_id, str) and marker_id:
            self._poi_selection = marker_id
        return True

    def consume_manual_camera(self):
        pending, self._manual_pending = self._manual_pending, False
        return pending

    def consume_poi_selection(self):
        marker_id, self._poi_selection = self._poi_selection, None
        return marker_id

    def update_position(self, position, follow_enabled):
        if self._devtools is None:
            raise RuntimeError("3D vehicle tracking is not ready")
        if position is not None and not isinstance(position, GeoPoint):
            raise TypeError("Vehicle tracking requires an SI GeoPoint")
        document = (
            None
            if position is None
            else {"latitude_rad": position.latitude_rad, "longitude_rad": position.longitude_rad}
        )
        result = self._devtools.command(
            self._target,
            "Runtime.evaluate",
            {
                "expression": f"window.ORCUpdateVehicle({json.dumps(document)}, {json.dumps(follow_enabled)})",
                "returnByValue": True,
            },
        )
        if result.get("exceptionDetails") or result.get("result", {}).get("value") is not True:
            raise RuntimeError("3D vehicle tracking rejected the update")

    def update_poi_overlay(self, state):
        if self._devtools is None:
            raise RuntimeError("3D POI overlay is not ready")
        if not isinstance(state, PoiOverlayState):
            raise TypeError("3D POI overlay requires PoiOverlayState")
        result = self._devtools.command(
            self._target,
            "Runtime.evaluate",
            {
                "expression": f"window.ORCUpdatePois({json.dumps(state.document())})",
                "returnByValue": True,
            },
        )
        if result.get("exceptionDetails") or result.get("result", {}).get("value") is not True:
            raise RuntimeError("3D POI overlay rejected the update")

    def update_route_overlay(self, state):
        if self._devtools is None:
            raise RuntimeError("3D route overlay is not ready")
        if not isinstance(state, RouteOverlayState):
            raise TypeError("3D route overlay requires RouteOverlayState")
        result = self._devtools.command(
            self._target,
            "Runtime.evaluate",
            {
                "expression": f"window.ORCUpdateRoute({json.dumps(state.document())})",
                "returnByValue": True,
            },
        )
        if result.get("exceptionDetails") or result.get("result", {}).get("value") is not True:
            raise RuntimeError("3D route overlay rejected the update")

    def close(self):
        resources, self._resources = self._resources, None
        self._browser = self._server = self._size = None
        self._devtools = self._target = None
        self.layer_controls = MapLayerControls()
        self._manual_revision = 0
        self._manual_pending = False
        self._poi_selection = None
        try:
            if resources is not None:
                # Close the browser while attached, before the Tk host is destroyed.
                resources.close()
        finally:
            self._embedder.clear()
