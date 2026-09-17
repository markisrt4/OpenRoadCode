# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.weather import WeatherAlert
from messaging.publisher_if import PublisherIf

from .topics import WEATHER_ALERT_TOPIC
from .weather_alert_codec import encode_weather_alert


class WeatherAlertPublisher:
    """Publish normalized weather alert events."""

    def __init__(self, publisher: PublisherIf) -> None:
        self._publisher = publisher

    def publish(self, alert: WeatherAlert) -> None:
        self._publisher.publish(WEATHER_ALERT_TOPIC, encode_weather_alert(alert))
