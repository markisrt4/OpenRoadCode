from __future__ import annotations

from typing import Protocol


class RadioInputAdapterIf(Protocol):
    """Lifecycle contract for devices that map input into radio operations."""

    def connect(self) -> None:
        """Connect the input device and begin dispatching radio operations."""
        ...

    def disconnect(self) -> None:
        """Stop dispatching operations and disconnect the input device."""
        ...
