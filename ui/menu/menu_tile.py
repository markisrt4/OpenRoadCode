from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MenuTile:
    """Describe one selectable navigation tile."""

    key: str
    title: str
    subtitle: str
    detail: str
