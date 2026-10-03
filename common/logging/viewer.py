# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Attach to ORC logs: python -m common.logging.viewer [--level DEBUG]."""

from __future__ import annotations
import argparse
import json
import os
import threading
from .structured import MAX_EVENT_BYTES, level_number, log_path, validate_event


def readable(item: dict) -> str:
    context = {
        k: v
        for k, v in item.items()
        if k not in {"timestamp", "level", "component", "message", "event", "pid", "stack_trace"}
    }
    suffix = " " + json.dumps(context, ensure_ascii=True) if context else ""
    # Escape control characters so log content cannot inject terminal commands.
    message = json.dumps(str(item["message"]), ensure_ascii=True)[1:-1]
    component = json.dumps(item["component"], ensure_ascii=True)[1:-1]
    event_name = json.dumps(item["event"], ensure_ascii=True)[1:-1]
    return f"{item['timestamp']} {item['level']:8} {component} [{event_name}] {message}{suffix}"


def follow(
    *,
    path=None,
    level="INFO",
    component=None,
    stop=None,
    output=print,
    from_end=False,
    start_offset=None,
):
    path = path or log_path()
    stop = stop or threading.Event()
    threshold = level_number(level)
    stream = None
    initial = True
    pending = ""
    try:
        while True:
            if stream is None:
                try:
                    stream = path.open(encoding="utf-8", errors="replace")
                except FileNotFoundError:
                    if stop.is_set():
                        break
                    stop.wait(0.1)
                    continue
                if initial and start_offset is not None:
                    inode, offset = start_offset
                    if os.fstat(stream.fileno()).st_ino == inode:
                        stream.seek(offset)
                elif initial and from_end:
                    stream.seek(0, 2)
                initial = False
            line = stream.readline(MAX_EVENT_BYTES)
            if line:
                pending += line
                if len(pending) > MAX_EVENT_BYTES:
                    pending = ""
                    while line and not line.endswith("\n"):
                        line = stream.readline(MAX_EVENT_BYTES)
                    continue
                if not pending.endswith("\n"):
                    continue
                try:
                    item = json.loads(pending)
                    validate_event(item)
                    if level_number(item["level"]) >= threshold and (
                        not component
                        or item["component"] == component
                        or item["component"].startswith(component + ".")
                    ):
                        output(readable(item))
                except (ValueError, KeyError, TypeError):
                    pass
                pending = ""
                continue
            try:
                replaced = os.fstat(stream.fileno()).st_ino != path.stat().st_ino
            except FileNotFoundError:
                replaced = False
            if replaced:
                stream.close()
                stream = None
                pending = ""
            elif stop.is_set():
                break
            stop.wait(0.1)
    finally:
        if stream:
            stream.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    parser.add_argument("--component", help="Component name or dotted prefix")
    parser.add_argument("--from-end", action="store_true", help="Only show newly appended events")
    args = parser.parse_args()
    try:
        follow(level=args.level, component=args.component, from_end=args.from_end)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
