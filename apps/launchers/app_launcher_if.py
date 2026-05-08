from abc import ABC, abstractmethod
from typing import Callable, Optional


StatusCallback = Optional[Callable[[str], None]]


class AppLauncherIf(ABC):
    @abstractmethod
    def launch(
        self,
        remote_display: str = ":2",
        set_status: StatusCallback = None,
    ) -> None:
        pass

    @abstractmethod
    def stop(
        self,
        set_status: StatusCallback = None,
    ) -> None:
        pass

    @abstractmethod
    def toggle(
        self,
        remote_display: str = ":2",
        set_status: StatusCallback = None,
    ) -> bool:
        pass

    @abstractmethod
    def is_running(self) -> bool:
        pass