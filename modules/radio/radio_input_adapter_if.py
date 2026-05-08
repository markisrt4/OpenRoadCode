from abc import ABC, abstractmethod


class RadioInputAdapterIf(ABC):
    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass
