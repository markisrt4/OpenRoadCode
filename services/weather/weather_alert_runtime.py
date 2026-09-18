# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Background NWS alert polling driven by public navigation position telemetry."""

from __future__ import annotations

import math
import threading

from controllers.weather import WeatherLocation
from messaging.contracts.navigation import (
    POSITION_STATE_TOPIC,
    PositionStateMessage,
    decode_position_state,
)
from messaging.message_dispatcher import MessageDispatcher
from messaging.subscriber_if import SubscriberIf


class WeatherAlertRuntime:
    """Poll active alerts for the latest navigation position and publish changes."""

    def __init__(
        self,
        provider,
        alert_publisher,
        subscriber: SubscriberIf,
        *,
        poll_interval_seconds: float = 60.0,
    ) -> None:
        if poll_interval_seconds < 30.0:
            raise ValueError("weather alert polling interval must be at least 30 seconds")
        self._provider = provider
        self._alert_publisher = alert_publisher
        self._period_s = poll_interval_seconds
        self._lock = threading.Lock()
        self._location: WeatherLocation | None = None
        self._active_alerts = {}
        self._stop_event = threading.Event()
        self._dispatcher = MessageDispatcher(subscriber)
        self._dispatcher.register(
            POSITION_STATE_TOPIC,
            decode_position_state,
            self._on_position_state,
        )

    def run(self) -> None:
        """Receive navigation positions and poll alerts until closed."""
        self._stop_event.clear()
        self._dispatcher.start()
        try:
            while not self._stop_event.is_set():
                with self._lock:
                    location = self._location
                if location is not None:
                    self.poll_once(location)
                self._stop_event.wait(self._period_s)
        finally:
            self.close()

    def poll_once(self, location: WeatherLocation) -> int:
        """Poll one location and publish only alerts that are new or changed."""
        alerts = self._provider.active_alerts(location)
        current = {alert.alert_id: alert for alert in alerts}
        published = 0
        for alert_id, alert in current.items():
            if self._active_alerts.get(alert_id) != alert:
                self._alert_publisher.publish(alert)
                published += 1
        self._active_alerts = current
        return published

    def close(self) -> None:
        self._stop_event.set()
        self._dispatcher.close()

    def _on_position_state(self, message: PositionStateMessage) -> None:
        latitude_rad = message.data.latitude_rad
        longitude_rad = message.data.longitude_rad
        if latitude_rad is None or longitude_rad is None:
            return
        if message.data.fix_mode is not None and message.data.fix_mode < 2:
            return
        with self._lock:
            self._location = WeatherLocation(
                latitude=math.degrees(latitude_rad),
                longitude=math.degrees(longitude_rad),
                name=f"{math.degrees(latitude_rad):.5f}, {math.degrees(longitude_rad):.5f}",
                source=message.source,
            )
