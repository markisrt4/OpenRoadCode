"""Shared, domain-neutral helpers for curses frontends."""

import curses


def addstr(screen, row: int, column: int, text: str, attributes: int = 0) -> None:
    """Draw clipped text while tolerating terminal resize races."""
    height, width = screen.getmaxyx()
    if row < 0 or row >= height or column < 0 or column >= width:
        return
    try:
        screen.addnstr(row, column, text, max(0, width - column - 1), attributes)
    except curses.error:
        pass


def format_value(
    value: float | int | None,
    unit: str = "",
    precision: int = 1,
) -> str:
    """Format an optional numeric value and unit."""
    if value is None:
        return "--"
    if isinstance(value, int):
        return f"{value} {unit}".strip()
    return f"{value:.{precision}f} {unit}".strip()
