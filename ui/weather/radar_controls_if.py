# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Interactive radar views bind requests through the shared UI contracts."""

from abc import abstractmethod
from ui.weather.radar_ui_if import RadarUiIf
from ui.weather.radar_request_handler_if import RadarRequestHandlerIf


class RadarControlsIf(RadarUiIf):
    @abstractmethod
    def set_radar_request_handler(self, handler: RadarRequestHandlerIf | None) -> None:
        """Connect or disconnect semantic radar actions.

        @param handler Radar request consumer, or None to disable actions.
        """
        ...
