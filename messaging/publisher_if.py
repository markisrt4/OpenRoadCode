from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

class PublisherIf(ABC):
    @abstractmethod
    def publish(self, topic: str, payload: Mapping[str, Any]) -> None:
        ...

    def close(self) -> None:
        pass
