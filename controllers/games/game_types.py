"""Types used by the native Linux game launcher."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TermuxProotRuntimeConfig:
    """Termux/proot-only launch and X11 compatibility settings.

    ``rendering`` describes the application's requirement rather than any
    specific Android device. ``auto`` allows the runtime to use an available
    accelerated bridge; ``software`` forces Mesa software rendering.
    """

    environment: dict[str, str] = field(default_factory=dict)
    rendering: str = "auto"
    window_name: str | None = None
    window_class: str | None = None

    def __post_init__(self) -> None:
        if self.rendering not in {"auto", "software"}:
            raise ValueError(f"unsupported Termux/proot rendering policy: {self.rendering}")


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
    termux_proot: TermuxProotRuntimeConfig = field(default_factory=TermuxProotRuntimeConfig)
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
