# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.automotive.automotive_telemetry_profile import AutomotiveTelemetryProfile
from messaging.contracts.automotive.telemetry_profile_request import encode_automotive_telemetry_profile_request
from messaging.contracts.automotive.topics import AUTOMOTIVE_TELEMETRY_PROFILE_REQUEST_TOPIC
from messaging.publisher_if import PublisherIf


class AutomotiveTelemetryProfileRequestPublisher:
    def __init__(self, publisher: PublisherIf, *, source: str = "orc-ui") -> None:
        self._publisher = publisher
        self._source = source

    def publish(self, profile: AutomotiveTelemetryProfile) -> None:
        self._publisher.publish(
            AUTOMOTIVE_TELEMETRY_PROFILE_REQUEST_TOPIC,
            encode_automotive_telemetry_profile_request(profile, source=self._source),
        )
