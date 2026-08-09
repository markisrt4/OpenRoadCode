from abc import ABC, abstractmethod


class UiIf(ABC):
    """Lifecycle contract implemented by a complete frontend.

    A frontend owns its toolkit application, top-level windows, event loop,
    and composed screens. Domain-specific UI contracts intentionally do not
    inherit this lifecycle.
    """

    @abstractmethod
    def initialize(self) -> bool:
        """Create resources and leave the frontend ready to run.

        @return True when initialization succeeds.
        """
        ...

    @abstractmethod
    def run(self) -> None:
        """Run the frontend event loop until it is asked to exit."""
        ...

    @abstractmethod
    def shutdown(self) -> None:
        """Release frontend resources; repeated calls must be safe."""
        ...
