"""Types used by the native Linux game launcher."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class GameDefinition:
    """Configuration describing an externally installed native game."""

    name: str
    command: tuple[str, ...]
    description: str = ""
    category: str = "casual"
    icon: str | None = None
    enabled: bool = True
    environment: dict[str, str] = field(default_factory=dict)
    termux_package: str | None = None
    termux_dependencies: tuple[str, ...] = ()
    debian_package: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("game name must not be empty")
        if not self.command:
            raise ValueError("game command must not be empty")
        if not self.category.strip():
            raise ValueError("game category must not be empty")
