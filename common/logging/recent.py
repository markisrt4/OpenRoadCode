# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Bounded, read-only pages from the configured JSON log store."""

from __future__ import annotations

from collections import deque
from contextlib import ExitStack
import fcntl
import json
import os
from pathlib import Path
import re

from .structured import MAX_EVENT_BYTES, level_number, log_path, validate_event

SCAN_BYTES = 256 * 1024
RESPONSE_BYTES = 256 * 1024
MAX_EVENTS = 200
BACKUPS = 4


def _cursor(value: str) -> tuple[int, int, int, int]:
    if not re.fullmatch(r"\d{1,20}:\d{1,20}:\d{1,20}:[01]", value):
        raise ValueError("Invalid log cursor")
    result = tuple(int(part) for part in value.split(":"))
    if any(part > 2**63 - 1 for part in result):
        raise ValueError("Invalid log cursor")
    return result


def _item(line: bytes, threshold: int, component: str | None) -> dict | None:
    try:
        value = json.loads(line)
        validate_event(value)
        if level_number(value["level"]) < threshold:
            return None
        if component and not (
            value["component"] == component or value["component"].startswith(component + ".")
        ):
            return None
        return value
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, RecursionError):
        return None


def read_recent(
    *, path: Path | None = None, cursor: str = "", level: str = "INFO", component: str = ""
) -> dict:
    """Read recent history or the next bounded page, following retained rotations.

    Cursors contain only file identity, byte position, and oversized-line state;
    clients cannot select a path. Missing/expired cursors reset to recent history.
    """
    threshold = level_number(level)
    if len(component) > 128 or (component and not re.fullmatch(r"[\w.-]+", component)):
        raise ValueError("Invalid log component")
    position = _cursor(cursor) if cursor else None
    path = path or log_path()
    with ExitStack() as stack:
        # The writer's shared lock makes rotation plus file enumeration atomic.
        # Never create a file or directory merely to view logs.
        try:
            lock = stack.enter_context(path.with_suffix(".lock").open("rb"))
        except FileNotFoundError:
            lock = None
        if lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
        files = []
        for candidate in [Path(f"{path}.{i}") for i in range(BACKUPS, 0, -1)] + [path]:
            try:
                stream = stack.enter_context(candidate.open("rb"))
            except FileNotFoundError:
                continue
            stat = os.fstat(stream.fileno())
            files.append((stream, stat))
        if not files:
            return {"events": [], "cursor": "", "reset": bool(cursor), "has_more": False}
        match = next(
            (
                i
                for i, (_, s) in enumerate(files)
                if position and (s.st_dev, s.st_ino) == position[:2] and position[2] <= s.st_size
            ),
            None,
        )
        recent = match is None
        reset = bool(cursor) and recent
        first = match
        tail_bytes = 0
        if recent:
            for first in range(len(files) - 1, -1, -1):
                tail_bytes += files[first][1].st_size
                if tail_bytes >= SCAN_BYTES:
                    break
        stream, stat = files[first]
        offset = max(0, tail_bytes - SCAN_BYTES) if recent else position[2]
        skipping = bool(offset) if recent else bool(position[3])
        # An initial tail starts inside an unknown record; skip it deliberately.
        stream.seek(offset)
        events = deque()
        used = 0
        scanned = 0
        has_more = False
        for index in range(first, len(files)):
            stream, stat = files[index]
            if index != first:
                offset = 0
                skipping = False
                stream.seek(0)
            while stream.tell() < stat.st_size:
                before = stream.tell()
                remaining = SCAN_BYTES - scanned
                if remaining <= 0:
                    has_more = True
                    break
                line = stream.readline(min(MAX_EVENT_BYTES + 1, remaining))
                scanned += len(line)
                complete = line.endswith(b"\n")
                if skipping:
                    skipping = not complete
                    offset = stream.tell()
                    continue
                if not complete:
                    if len(line) >= MAX_EVENT_BYTES:
                        skipping = True
                        offset = stream.tell()
                        continue
                    if len(line) == remaining:
                        stream.seek(before)
                        has_more = True
                        break
                    # A writer's incomplete final record is retried next time.
                    stream.seek(before)
                    break
                value = _item(line, threshold, component) if len(line) <= MAX_EVENT_BYTES else None
                if value is not None:
                    cost = len(json.dumps(value, ensure_ascii=True).encode())
                    if not recent and (len(events) >= MAX_EVENTS or used + cost > RESPONSE_BYTES):
                        stream.seek(before)
                        has_more = True
                        break
                    events.append(value)
                    used += cost
                    while len(events) > MAX_EVENTS or used > RESPONSE_BYTES:
                        used -= len(json.dumps(events.popleft(), ensure_ascii=True).encode())
                offset = stream.tell()
            if has_more:
                break
            if index < len(files) - 1 and scanned >= SCAN_BYTES:
                has_more = True
                break
        return {
            "events": list(events),
            "cursor": f"{stat.st_dev}:{stat.st_ino}:{offset}:{int(skipping)}",
            "reset": reset,
            "has_more": has_more,
        }
