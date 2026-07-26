from abc import ABC, abstractmethod
from enum import Enum, auto

class UiAction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    SELECT = auto()
    BACK = auto()
    HOME = auto()

    INCREASE = auto()
    DECREASE = auto()

    ROTATE = auto()
    PRESS = auto()
    
    
class UiEventHandlerIf(ABC):
    
    @abstractmethod
    def handle_ui_action(self, action: UiAction) -> None:
        ...