# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Transport-independent telemetry publisher contract."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import object


class TelemetryPublisherIf(ABC):
    """Publish normalized OpenRoadCode telemetry without exposing transport details."""

    @abstractmethod
    def publish(self, topic: str, payload: Mapping[str, object]) -> None:
        """Publish one telemetry payload on the named topic."""
        ...

    def close(self) -> None:
        """Release publisher resources when the implementation owns any."""
