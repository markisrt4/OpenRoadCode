# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Present navigation position bus messages in the Car UI shell."""

from __future__ import annotations

import math
from collections.abc import Callable

from messaging.contracts.navigation import PositionStateMessage


class BusPositionPresenter:
    """Translate public navigation position messages into shell location state."""

    def __init__(
        self,
        *,
        set_position: Callable[[float | None, float | None], None],
        set_status: Callable[[str], None] | None = None,
    ) -> None:
        self._set_position = set_position
        self._set_status = set_status

    def set_position_message(self, message: PositionStateMessage) -> None:
        """Apply one decoded position message to the shell."""
        data = message.data
        if data.latitude_rad is None or data.longitude_rad is None:
            self._set_position(None, None)
            self._publish_status("Position unavailable")
            return
        self._set_position(
            math.degrees(data.latitude_rad),
            math.degrees(data.longitude_rad),
        )
        if data.satellites_used is not None:
            visible = data.satellites_visible if data.satellites_visible is not None else "?"
            self._publish_status(
                f"Navigation position acquired: {data.satellites_used}/{visible} satellites"
            )
        elif data.accuracy_m is not None:
            self._publish_status(f"Navigation position acquired: ±{data.accuracy_m:.0f} m")
        else:
            self._publish_status("Navigation position acquired")

    def set_error(self) -> None:
        """Clear the shell position after a navigation transport failure."""
        self._set_position(None, None)

    def _publish_status(self, message: str) -> None:
        if self._set_status is not None:
            self._set_status(message)
