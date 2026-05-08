from abc import ABC, abstractmethod
from typing import Any


class HardwareDeviceIf(ABC):
    def __init__(self, name: str):
        self.name = name
        self.running = False
        self.available = False
        self.last_error: str | None = None

    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def status(self) -> dict[str, Any]:
        pass

    def is_running(self) -> bool:
        return self.running

    def is_available(self) -> bool:
        return self.available