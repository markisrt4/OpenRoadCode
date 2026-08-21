# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from controllers.navigation.navigation_state import PositionState
from messaging.publisher_if import PublisherIf

from .position_state_codec import encode_position_state
from .topics import POSITION_STATE_TOPIC


class PositionStatePublisher:
    """Publish normalized geographic position snapshots."""

    def __init__(self, publisher: PublisherIf) -> None:
        self._publisher = publisher

    def publish(self, state: PositionState) -> None:
        self._publisher.publish(POSITION_STATE_TOPIC, encode_position_state(state))
