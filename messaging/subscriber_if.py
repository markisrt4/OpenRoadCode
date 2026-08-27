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
        """Subscribe to a topic or transport-specific topic prefix.

        @param topic Public topic name or supported transport-specific prefix.
        """
        ...

    @abstractmethod
    def receive(self) -> tuple[str, Mapping[str, Any]]:
        """Block until one encoded message is received.

        @return Pair containing the received topic and JSON-compatible payload.
        """
        ...

    def close(self) -> None:
        """Release subscriber resources when the implementation owns any."""
