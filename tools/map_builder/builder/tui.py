# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Curses region selector for the OpenRoadCode map builder."""

from __future__ import annotations

import curses
from collections import defaultdict
from dataclasses import dataclass, field

from .geofabrik import Region, region_map, validate_selection


@dataclass
class State:
    cursor: int = 0
    offset: int = 0
    query: str = ""
    expanded: set[str] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class VisibleRegion:
    region: Region
    depth: int
    has_children: bool


def visible_regions(
    regions: list[Region],
    expanded: set[str],
    query: str = "",
) -> list[VisibleRegion]:
    """Flatten the currently visible portion of the Geofabrik region tree."""
    mapping = region_map(regions)
    children: dict[str | None, list[Region]] = defaultdict(list)
    for region in regions:
        parent = region.parent if region.parent in mapping else None
        children[parent].append(region)
    for siblings in children.values():
        siblings.sort(key=lambda region: (region.name.casefold(), region.id))

    normalized_query = query.casefold().strip()
    included: set[str] | None = None
    if normalized_query:
        included = set()
        for region in regions:
            if normalized_query not in region.id.casefold() and normalized_query not in region.name.casefold():
                continue
            current: Region | None = region
            while current is not None and current.id not in included:
                included.add(current.id)
                current = mapping.get(current.parent) if current.parent else None

    result: list[VisibleRegion] = []

    def visit(region: Region, depth: int) -> None:
        if included is not None and region.id not in included:
            return
        descendants = children.get(region.id, [])
        result.append(VisibleRegion(region, depth, bool(descendants)))
        if included is not None or region.id in expanded:
            for child in descendants:
                visit(child, depth + 1)

    for root in children.get(None, []):
        visit(root, 0)
    return result


def expanded_ancestors(selected: set[str], mapping: dict[str, Region]) -> set[str]:
    """Return ancestors that must be open to reveal the selected regions."""
    expanded: set[str] = set()
    for region_id in selected:
        parent = mapping[region_id].parent
        while parent and parent in mapping:
            expanded.add(parent)
            parent = mapping[parent].parent
    return expanded


def select_regions(
    regions: list[Region],
    initial_selected: set[str] | None = None,
) -> list[Region] | None:
    mapping = region_map(regions)
    selected = set(initial_selected or ()) & mapping.keys()
    try:
        validate_selection((mapping[region_id] for region_id in selected), mapping)
    except ValueError:
        selected.clear()

    def run(stdscr) -> list[Region] | None:
        curses.curs_set(0)
        state = State(expanded=expanded_ancestors(selected, mapping))
        status = "RIGHT expand  LEFT collapse  SPACE select  ENTER accept  / search  q quit"
        while True:
            height, width = stdscr.getmaxyx()
            visible = visible_regions(regions, state.expanded, state.query)
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
            for row, item in enumerate(visible[state.offset:state.offset + page], start=3):
                absolute = state.offset + row - 3
                region = item.region
                marker = "[x]" if region.id in selected else "[ ]"
                if item.has_children:
                    disclosure = "▼" if state.query or region.id in state.expanded else "▶"
                else:
                    disclosure = " "
                text = f"{marker} {'  ' * item.depth}{disclosure} {region.name}  ({region.id})"
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
            elif key == curses.KEY_RIGHT and visible:
                item = visible[state.cursor]
                if item.has_children and not state.query:
                    if item.region.id in state.expanded:
                        state.expanded.remove(item.region.id)
                    else:
                        state.expanded.add(item.region.id)
            elif key == curses.KEY_LEFT and visible and not state.query:
                item = visible[state.cursor]
                if item.region.id in state.expanded:
                    state.expanded.remove(item.region.id)
                elif item.region.parent:
                    parent_index = next(
                        (index for index, row in enumerate(visible) if row.region.id == item.region.parent),
                        state.cursor,
                    )
                    state.cursor = parent_index
            elif key == " " and visible:
                region = visible[state.cursor].region
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
                status = "RIGHT expand  LEFT collapse  SPACE select  ENTER accept  / search  q quit"
            elif key in ("c", "C"):
                state.query = ""
                state.cursor = 0
                state.offset = 0
            elif key in ("b", "B", "\n", "\r", curses.KEY_ENTER):
                if not selected:
                    status = "Select at least one region first"
                else:
                    result = [mapping[rid] for rid in selected]
                    validate_selection(result, mapping)
                    return sorted(result, key=lambda r: r.id)
        return None

    return curses.wrapper(run)
