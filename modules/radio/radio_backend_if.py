from abc import ABC, abstractmethod


class RadioBackendIf(ABC):
    @abstractmethod
    def start(self) -> str:
        pass

    @abstractmethod
    def stop(self) -> str:
        pass

    @abstractmethod
    def set_frequency(self, frequency_hz: int) -> str:
        pass

    @abstractmethod
    def get_frequency(self) -> int:
        pass

    @abstractmethod
    def set_mode(self, mode: str, bandwidth: int) -> str:
        pass
