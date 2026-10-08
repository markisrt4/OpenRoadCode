"""Open user-selected Earth destinations in an ordinary native browser window."""

import os
import shutil
import subprocess
from urllib.parse import urlsplit

from apps.launchers.external_window_manager import x11_environment
from apps.launchers.graphics_environment import graphics_environment
from common.logging.logging_paths import logging_file_path
from controllers.poi.poi_action_executor_if import PoiActionExecutorIf
from ui.navigation.poi_models import PoiActionKind


class EarthExplorationActions(PoiActionExecutorIf):
    """Route Earth links to native Chromium, retaining other platform actions."""

    def __init__(self, fallback):
        self._fallback = fallback

    def execute(self, poi, action) -> str:
        if action.provider_id != "google-earth-explore":
            return self._fallback.execute(poi, action)
        parsed = urlsplit(action.uri or "")
        if (action.kind is not PoiActionKind.OPEN_WEBSITE or parsed.scheme != "https"
                or parsed.netloc != "earth.google.com"
                or not parsed.path.startswith("/web/search/")):
            raise ValueError("Invalid Google Earth exploration link")
        browser = next((path for name in ("chromium-browser", "chromium", "google-chrome")
                        if (path := shutil.which(name))), None)
        if browser is None:
            raise RuntimeError("Install native Chromium to explore this place in Google Earth")
        environment = graphics_environment(x11_environment(os.environ.get("DISPLAY", ":1")))
        # Normal browser ownership: no embedding, GPS subscriber, DevTools,
        # injected JavaScript, or ORC camera controls.
        with logging_file_path("openroadcode", "earth-explore.log").open("a", encoding="utf-8") as log:
            subprocess.Popen([browser, "--new-window", "--password-store=basic", action.uri],
                             env=environment, stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True)
        return "Opened selected place in Google Earth"
