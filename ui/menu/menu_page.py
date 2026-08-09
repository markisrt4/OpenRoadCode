from dataclasses import dataclass

from ui.menu.menu_tile import MenuTile


@dataclass(frozen=True, slots=True)
class MenuPage:
    """Describe a titled, column-oriented page of navigation tiles."""

    title: str
    tiles: tuple[MenuTile, ...]
    columns: int = 3
