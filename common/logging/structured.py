# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""ORC JSON Lines logging with a process-safe, bounded shared store."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import fcntl
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
from uuid import uuid4

_OPERATION = ContextVar("orc_log_operation", default=None)
LEVELS = {
    name: getattr(logging, name) for name in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
}
MAX_EVENT_BYTES = 64 * 1024
_OVERRIDE_LEVELS: dict[str, int] = {}


def log_path() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))).expanduser()
    return (
        Path(os.environ.get("ORC_LOG_DIR", str(root / "openroadcode/logs"))).expanduser()
        / "orc.jsonl"
    )


def level_number(name: str) -> int:
    try:
        return LEVELS[name.upper()]
    except KeyError:
        raise ValueError(f"Unknown ORC log level: {name}") from None


def current_operation() -> str | None:
    return _OPERATION.get()


@contextmanager
def operation(operation_id: str | None = None):
    value = operation_id or uuid4().hex
    token = _OPERATION.set(value)
    try:
        yield value
    finally:
        _OPERATION.reset(token)


def event(logger: logging.Logger, level: int, name: str, message: str, **fields) -> None:
    fields = dict(fields)
    if current_operation() and "operation_id" not in fields:
        fields["operation_id"] = current_operation()
    logger.log(level, message, extra={"event": name, "fields": fields})


class JsonFormatter(logging.Formatter):
    def format(self, record):
        result = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "component": record.name,
            "event": getattr(record, "event", "log.message"),
            "message": record.getMessage(),
            "pid": record.process,
        }
        # Context cannot replace required schema fields.
        result.update({k: v for k, v in getattr(record, "fields", {}).items() if k not in result})
        if record.exc_info:
            result["exception_type"] = record.exc_info[0].__name__
            result["error_message"] = str(record.exc_info[1])
            result["stack_trace"] = self.formatException(record.exc_info)
        return json.dumps(result, ensure_ascii=False, default=str)


class JsonStore:
    """Five files of at most 10 MiB each; all writers share an advisory lock.

    Open the active file after acquiring the lock so rotation cannot strand a
    writer on a renamed inode. Individual oversized events are replaced safely.
    """

    def __init__(self, path: Path | None = None, *, max_bytes=10 * 1024 * 1024, backups=4):
        if max_bytes < 1024 or backups < 0:
            raise ValueError("Log files must allow at least 1024 bytes; backups cannot be negative")
        self.path = path or log_path()
        self.max_bytes = max_bytes
        self.backups = backups
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._thread_lock = threading.Lock()
        self._errors = {}

    def append(self, item: dict) -> dict | None:
        with self._thread_lock:
            # Rate-limit repeated warnings/errors per process and event, with a
            # suppression summary on the next occurrence after five seconds.
            if logging.WARNING <= level_number(item["level"]) < logging.CRITICAL:
                key = (item["component"], item["event"], item["level"], item.get("operation_id"))
                now = time.monotonic()
                last, count = self._errors.get(key, (-float("inf"), 0))
                if now - last < 5:
                    self._errors[key] = (last, count + 1)
                    return
                if count:
                    item = dict(item, suppressed_count=count)
                self._errors[key] = (now, 0)
                if len(self._errors) > 1024:
                    self._errors.pop(next(iter(self._errors)))
            line = (json.dumps(item, ensure_ascii=False, default=str) + "\n").encode("utf-8")
            if len(line) > min(MAX_EVENT_BYTES, self.max_bytes):
                item = {
                    k: (item[k][:128] if isinstance(item[k], str) else item[k])
                    for k in ("timestamp", "level", "component", "event", "pid")
                }
                item.update(message="Log event exceeded size limit", truncated=True)
                line = (json.dumps(item) + "\n").encode()
            with self.path.with_suffix(".lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                size = self.path.stat().st_size if self.path.exists() else 0
                if size + len(line) > self.max_bytes:
                    if not self.backups:
                        self.path.unlink(missing_ok=True)
                    for index in range(self.backups, 0, -1):
                        source = self.path if index == 1 else Path(f"{self.path}.{index - 1}")
                        if source.exists():
                            source.replace(Path(f"{self.path}.{index}"))
                with self.path.open("ab") as target:
                    target.write(line)
            return item


class StoreHandler(logging.Handler):
    def __init__(self, store, *, stderr=False):
        super().__init__()
        self.store = store
        self.stderr = stderr
        self.setFormatter(JsonFormatter())

    def emit(self, record):
        try:
            item = self.store.append(json.loads(self.format(record)))
            if item is not None and self.stderr:
                print(json.dumps(item, ensure_ascii=False, default=str), file=sys.stderr)
        except Exception:
            self.handleError(record)


def configure_logging(*, level: str | None = None, stderr: bool = True) -> JsonStore:
    selected = level or os.environ.get("ORC_LOG_LEVEL", "INFO")
    threshold = level_number(selected)
    overrides = []
    for entry in filter(None, os.environ.get("ORC_LOG_COMPONENT_LEVELS", "").split(",")):
        component, component_level = entry.split("=", 1)
        if not component.strip():
            raise ValueError("Log component override requires a component name")
        overrides.append((component.strip(), level_number(component_level.strip())))
    store = JsonStore()
    root = logging.getLogger()
    # Leave unrelated handlers installed by embedding applications alone.
    for handler in list(root.handlers):
        if getattr(handler, "_orc", False):
            root.removeHandler(handler)
            handler.close()
    root.setLevel(threshold)
    handler = StoreHandler(store, stderr=stderr)
    handler._orc = True
    root.addHandler(handler)
    for component, previous in _OVERRIDE_LEVELS.items():
        logging.getLogger(component).setLevel(previous)
    _OVERRIDE_LEVELS.clear()
    for component, component_level in overrides:
        _OVERRIDE_LEVELS[component] = logging.getLogger(component).level
        logging.getLogger(component).setLevel(component_level)
    return store


def validate_event(item: dict) -> None:
    """Validate required schema types and the UTC millisecond timestamp."""
    import re

    if not isinstance(item, dict):
        raise ValueError("Log event must be an object")
    for key in ("timestamp", "level", "component", "event", "message"):
        if not isinstance(item.get(key), str):
            raise ValueError(f"Log {key} must be a string")
    if item["level"] not in LEVELS:
        raise ValueError("Invalid severity")
    if type(item.get("pid")) is not int or item["pid"] <= 0:
        raise ValueError("Log pid must be a positive integer")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", item["timestamp"]):
        raise ValueError("Timestamp must be UTC with millisecond precision")
    datetime.fromisoformat(item["timestamp"])
    if not item["component"] or not item["event"]:
        raise ValueError("Log component and event cannot be empty")
    if "operation_id" in item and not isinstance(item["operation_id"], str):
        raise ValueError("Operation ID must be a string")


def collect_native_output(
    stream, store: JsonStore, pid: int, *, component: str = "map_renderer.output"
) -> None:
    """Drain native output without unbounded line allocation; retain source PID."""
    while line := stream.readline(MAX_EVENT_BYTES):
        if not line.endswith("\n") and len(line) == MAX_EVENT_BYTES:
            while remainder := stream.readline(MAX_EVENT_BYTES):
                if remainder.endswith("\n"):
                    break
            line = "Native log line exceeded size limit"
        try:
            item = json.loads(line)
            if not isinstance(item, dict) or not all(
                k in item for k in ("timestamp", "level", "component", "event", "message", "pid")
            ):
                raise ValueError("Unstructured output")
            validate_event(item)
        except (ValueError, TypeError, KeyError):
            item = {
                "timestamp": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
                "level": "INFO",
                "component": component,
                "event": "native.output",
                "message": line.rstrip(),
                "pid": pid,
            }
        try:
            store.append(item)
        except OSError as error:
            print(f"ORC log collection failed: {error}", file=sys.stderr)
    stream.close()
