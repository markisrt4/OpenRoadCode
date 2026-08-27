# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.route_guidance import RouteGuidanceState
from messaging.publisher_if import PublisherIf

from .route_guidance_state_codec import encode_route_guidance_state
from .topics import ROUTE_GUIDANCE_STATE_TOPIC


class RouteGuidanceStatePublisher:
    """Publish route-guidance snapshots."""

    def __init__(self, publisher: PublisherIf, *, source: str = "route_guidance") -> None:
        self._publisher = publisher
        self._source = source

    def publish(self, state: RouteGuidanceState) -> None:
        self._publisher.publish(
            ROUTE_GUIDANCE_STATE_TOPIC,
            encode_route_guidance_state(state, source=self._source),
        )
