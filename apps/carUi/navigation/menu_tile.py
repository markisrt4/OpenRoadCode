from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MenuTile:
    """Describe one selectable tile in a Car UI navigation page."""
    key: str
    title: str
    subtitle: str
    detail: str
