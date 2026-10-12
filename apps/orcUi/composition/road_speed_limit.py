# SPDX-License-Identifier: MIT
"""Composition-owned local road-limit worker and navigation observation."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import math

from common.resource_cleanup import ResourceCleanup, close_resources
from config.service_runtime_config import ServiceRuntimeConfigParser
from controllers.navigation.road_speed_limit_controller import RoadSpeedLimitController
from controllers.navigation.valhalla_speed_limit_provider import ValhallaSpeedLimitProvider
from protocols.valhalla.valhalla_http_client import ValhallaHttpClient
from services.automotive.automotive_service_cli import DEFAULT_RUNTIME_CONFIG
from ui.navigation.map_ui_if import GeoPoint


@dataclass
class RoadSpeedLimitComposition:
    controller: RoadSpeedLimitController
    workers: ThreadPoolExecutor

    def close(self) -> None:
        close_resources(self.controller.close,
                        lambda: self.workers.shutdown(wait=False, cancel_futures=True))


def configure_road_speed_limit(app, presentation, home) -> RoadSpeedLimitComposition:
    config = ServiceRuntimeConfigParser(DEFAULT_RUNTIME_CONFIG).load().navigation.route_planning
    with ResourceCleanup() as cleanup:
        workers = ThreadPoolExecutor(max_workers=1, thread_name_prefix="road-speed-limit")
        cleanup.callback(lambda: workers.shutdown(wait=False, cancel_futures=True))
        controller = RoadSpeedLimitController(
            ValhallaSpeedLimitProvider(ValhallaHttpClient(config.base_url, timeout_seconds=2.0)),
            home, app, lambda callback: workers.submit(callback),
        )
        cleanup.callback(controller.close)
        resource = RoadSpeedLimitComposition(controller, workers)
        def position_changed(state) -> None:
            if not config.enabled or config.backend != "valhalla" or state.is_cached or state.fix_mode not in (2, 3) or (
                state.latitude_deg is None or state.longitude_deg is None
            ):
                controller.update_position(None)
            else:
                controller.update_position(GeoPoint(math.radians(state.latitude_deg), math.radians(state.longitude_deg)), state.accuracy_m)
        presentation.observe_position(position_changed)
        position_changed(presentation.position)
        controller.start()
        cleanup.release()
        return resource
