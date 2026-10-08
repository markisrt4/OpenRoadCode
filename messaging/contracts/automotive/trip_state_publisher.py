# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Publisher for the public automotive trip-state contract."""

from controllers.automotive.trip_state import TripState
from messaging.publisher_if import PublisherIf
from .topics import TRIP_STATE_TOPIC
from .trip_state_codec import encode_trip_state


class TripStatePublisher:
    def __init__(self, publisher: PublisherIf, *, source: str = "trip-service") -> None:
        self._publisher = publisher
        self._source = source

    def publish(self, state: TripState) -> None:
        self._publisher.publish(TRIP_STATE_TOPIC, encode_trip_state(state, source=self._source))
