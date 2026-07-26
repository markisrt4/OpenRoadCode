from abc import ABC, abstractmethod

class UiIf(ABC):
    """
    TODO
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        ...
    
    @abstractmethod
    def shutdown(self) -> bool:
        ...

    @abstractmethod        
    def _create_window(self) -> bool:
        ...
        
    @abstractmethod
    def _destroy_window(self) -> bool:
        ...
