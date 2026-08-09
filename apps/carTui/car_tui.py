"""Curses shell, static routes, and home menu for Car TUI."""

import curses

from apps.carTui.car_tui_dependencies import CarTuiDependencies
from apps.carTui.screens import NavigationScreen, RadioScreen, VehicleScreen
from frontends.tui.curses_helpers import addstr


class CarTui:
    """Navigate statically composed vehicle destinations in one terminal."""

    MENU = (
        ("navigation", "Off-road navigation", "Heading, pitch, roll, motion, GPS"),
        ("vehicle", "Vehicle telemetry", "RPM, speed, temperatures, fuel, voltage"),
        ("radio", "Radio", "FM, scanner, AM airband, FM weather band"),
    )

    def __init__(
        self,
        dependencies: CarTuiDependencies,
        *,
        gps_enabled: bool = False,
    ) -> None:
        self._routes = {
            "navigation": NavigationScreen(
                dependencies.navigation_controller,
                gps_enabled=gps_enabled,
            ),
            "vehicle": VehicleScreen(dependencies.vehicle_manager),
            "radio": RadioScreen(dependencies.radios),
        }

    def run(self, window) -> None:
        """Run the home menu and selected destinations."""
        _configure_curses(window)
        selected = 0
        while True:
            self._render_home(window, selected)
            key = window.getch()
            if key in (ord("q"), ord("Q")):
                return
            if key in (curses.KEY_UP, ord("k"), ord("K")):
                selected = (selected - 1) % len(self.MENU)
            elif key in (curses.KEY_DOWN, ord("j"), ord("J")):
                selected = (selected + 1) % len(self.MENU)
            elif ord("1") <= key <= ord(str(len(self.MENU))):
                selected = key - ord("1")
                if not self._routes[self.MENU[selected][0]].run(window):
                    return
            elif key in (curses.KEY_ENTER, 10, 13):
                if not self._routes[self.MENU[selected][0]].run(window):
                    return

    def _render_home(self, window, selected: int) -> None:
        window.erase()
        height, width = window.getmaxyx()
        addstr(window, 1, 2, "OpenRoadCode Car TUI", curses.A_BOLD)
        addstr(window, 2, 0, "─" * max(0, width - 1))
        for index, (_key, title, detail) in enumerate(self.MENU):
            attr = curses.A_REVERSE | curses.A_BOLD if index == selected else 0
            addstr(window, 5 + index * 3, 4, f"{index + 1}. {title}", attr)
            addstr(window, 6 + index * 3, 8, detail, curses.A_DIM)
        addstr(window, height - 2, 2, "↑/↓ or j/k: select   Enter: open   q: quit")
        window.refresh()


def _configure_curses(window) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    window.nodelay(False)
    window.keypad(True)
    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_RED, -1)
