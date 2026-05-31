from abc import ABC, abstractmethod

class AudioControllerIf(ABC):

    @abstractmethod
    def volume_up(self, amount: str = "+5%") -> int:
        pass

    @abstractmethod
    def volume_down(self, amount: str = "-5%") -> int:
        pass

    @abstractmethod
    def get_volume_level(self) -> int:
        pass

    @abstractmethod
    def set_volume_level(self, level: int) -> None:
        pass
