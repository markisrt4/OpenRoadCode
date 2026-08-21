# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Transport-independent subscriber contract."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class SubscriberIf(ABC):
    """Receive OpenRoadCode messages without exposing transport details."""

    @abstractmethod
    def subscribe(self, topic: str) -> None:
        """Subscribe to a topic or transport-specific topic prefix."""
        ...

    @abstractmethod
    def receive(self) -> tuple[str, Mapping[str, Any]]:
        """Block until one message is received and return topic plus payload."""
        ...

    def close(self) -> None:
        """Release subscriber resources when the implementation owns any."""
