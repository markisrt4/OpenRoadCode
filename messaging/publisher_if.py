# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Transport-independent publisher contract."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any


class PublisherIf(ABC):
    """Publish OpenRoadCode messages without exposing transport details."""

    @abstractmethod
    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        """Publish one encoded payload on a topic.

        @param topic Public topic name used to route the message.
        @param payload JSON-compatible encoded contract payload.
        """
        ...

    def close(self) -> None:
        """Release publisher resources when the implementation owns any."""
