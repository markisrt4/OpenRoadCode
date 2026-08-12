"""Curses region selector for the OpenRoadCode map builder."""

from __future__ import annotations

import curses
from dataclasses import dataclass

from .geofabrik import Region, region_map, validate_selection


@dataclass
class State:
    cursor: int = 0
    offset: int = 0
    query: str = ""


def select_regions(regions: list[Region]) -> list[Region] | None:
    selected: set[str] = set()
    mapping = region_map(regions)

    def run(stdscr) -> list[Region] | None:
        curses.curs_set(0)
        state = State()
        status = "SPACE select  / search  ENTER build  q quit"
        while True:
            height, width = stdscr.getmaxyx()
            query = state.query.casefold()
            visible = [r for r in regions if not query or query in r.id.casefold() or query in r.name.casefold()]
            if not visible:
                state.cursor = 0
                state.offset = 0
            else:
                state.cursor = max(0, min(state.cursor, len(visible) - 1))
                page = max(1, height - 5)
                if state.cursor < state.offset:
                    state.offset = state.cursor
                if state.cursor >= state.offset + page:
                    state.offset = state.cursor - page + 1
            stdscr.erase()
            title = f"OpenRoadCode Map Builder | selected={len(selected)} | filter={state.query or '<none>'}"
            stdscr.addnstr(0, 0, title, width - 1, curses.A_BOLD)
            stdscr.addnstr(1, 0, status, width - 1)
            page = max(1, height - 5)
            for row, region in enumerate(visible[state.offset:state.offset + page], start=3):
                absolute = state.offset + row - 3
                marker = "[x]" if region.id in selected else "[ ]"
                depth = region.id.count("/")
                text = f"{marker} {'  ' * depth}{region.name}  ({region.id})"
                attr = curses.A_REVERSE if absolute == state.cursor else curses.A_NORMAL
                stdscr.addnstr(row, 0, text, width - 1, attr)
            stdscr.refresh()
            key = stdscr.get_wch()
            if key in ("q", "Q"):
                return None
            if key == curses.KEY_UP and visible:
                state.cursor = max(0, state.cursor - 1)
            elif key == curses.KEY_DOWN and visible:
                state.cursor = min(len(visible) - 1, state.cursor + 1)
            elif key == curses.KEY_PPAGE and visible:
                state.cursor = max(0, state.cursor - page)
            elif key == curses.KEY_NPAGE and visible:
                state.cursor = min(len(visible) - 1, state.cursor + page)
            elif key == " " and visible:
                region = visible[state.cursor]
                if region.id in selected:
                    selected.remove(region.id)
                    status = "Deselected " + region.name
                else:
                    candidate = [mapping[rid] for rid in selected] + [region]
                    try:
                        validate_selection(candidate, mapping)
                    except ValueError as exc:
                        status = str(exc)
                    else:
                        selected.add(region.id)
                        status = "Selected " + region.name
            elif key == "/":
                curses.echo()
                curses.curs_set(1)
                stdscr.move(2, 0)
                stdscr.clrtoeol()
                stdscr.addstr(2, 0, "Search: ")
                value = stdscr.getstr(2, 8, max(1, width - 9)).decode("utf-8", errors="replace")
                curses.noecho()
                curses.curs_set(0)
                state.query = value
                state.cursor = 0
                state.offset = 0
                status = "SPACE select  / search  ENTER build  q quit"
            elif key in ("c", "C"):
                state.query = ""
                state.cursor = 0
                state.offset = 0
            elif key in ("\n", "\r", curses.KEY_ENTER):
                if not selected:
                    status = "Select at least one region first"
                else:
                    result = [mapping[rid] for rid in selected]
                    validate_selection(result, mapping)
                    return sorted(result, key=lambda r: r.id)
        return None

    return curses.wrapper(run)
