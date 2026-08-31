"""Types used by the native Linux game launcher."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GameDefinition:
    """Configuration describing an externally installed native game."""

    name: str
    command: tuple[str, ...]
    description: str = ""
    enabled: bool = True
    environment: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("game name must not be empty")
        if not self.command:
            raise ValueError("game command must not be empty")
