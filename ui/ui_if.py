from abc import ABC, abstractmethod

class UiIf(ABC):
    """Lifecycle contract implemented by a complete user interface.

    Lifecycle operations are idempotent. Implementations return ``True`` when
    the requested final state has been reached, including when it was already
    reached, and ``False`` when the transition could not be completed.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """Create resources and leave the UI ready to receive updates."""
        ...
    
    @abstractmethod
    def shutdown(self) -> bool:
        """Release resources; repeated calls must be safe."""
        ...

    @abstractmethod        
    def _create_window(self) -> bool:
        """Create the implementation-specific window resources."""
        ...
        
    @abstractmethod
    def _destroy_window(self) -> bool:
        """Destroy window resources; repeated calls must be safe."""
        ...
