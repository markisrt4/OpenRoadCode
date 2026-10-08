# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Behavioral gates for the shared Python/native logging contract."""

import io
import json
import logging
import multiprocessing
import threading
from pathlib import Path

import pytest

from common.logging.structured import (
    MAX_EVENT_BYTES,
    JsonFormatter,
    JsonStore,
    StoreHandler,
    collect_native_output,
    configure_logging,
    current_operation,
    event,
    operation,
    validate_event,
)
from common.logging.viewer import follow, readable


def sample(**fields):
    return dict(
        timestamp="2026-10-03T15:04:12.123Z",
        level="INFO",
        component="navigation.routing",
        event="route.calculated",
        message="Route calculated",
        pid=123,
        **fields,
    )


def records(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_process(path, worker):
    store = JsonStore(Path(path), max_bytes=2048, backups=100)
    for index in range(20):
        store.append(sample(worker=worker, index=index))


def test_formatter_preserves_types_escapes_lines_and_protects_schema():
    record = logging.LogRecord(
        "navigation.routing", logging.INFO, "", 0, 'Route "accepted"\nnext line', (), None
    )
    record.event = "route.accepted"
    record.fields = {"point_count": 326, "available": True, "pid": "wrong", "level": "bad"}
    encoded = JsonFormatter().format(record)
    assert "\n" not in encoded
    item = json.loads(encoded)
    validate_event(item)
    assert item["point_count"] == 326 and item["available"] is True
    assert type(item["pid"]) is int and item["level"] == "INFO"


def test_exception_fields_are_available():
    try:
        raise RuntimeError("test failure")
    except RuntimeError:
        import sys

        record = logging.LogRecord(
            "navigation.routing", logging.ERROR, "", 0, "Route failed", (), sys.exc_info()
        )
    item = json.loads(JsonFormatter().format(record))
    validate_event(item)
    assert item["exception_type"] == "RuntimeError"
    assert item["error_message"] == "test failure"
    assert "RuntimeError: test failure" in item["stack_trace"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("timestamp", "2026-10-03"),
        ("level", "WARN"),
        ("component", ""),
        ("message", 4),
        ("event", None),
        ("pid", True),
        ("pid", "123"),
        ("operation_id", 4),
    ],
)
def test_invalid_native_schema_is_rejected(field, value):
    item = sample()
    item[field] = value
    with pytest.raises(ValueError):
        validate_event(item)


def test_rotation_enforces_total_budget_and_discards_oldest(tmp_path):
    store = JsonStore(tmp_path / "orc.jsonl", max_bytes=1024, backups=2)
    for index in range(80):
        store.append(sample(index=index))
    files = list(tmp_path.glob("orc.jsonl*"))
    assert len(files) == 3
    assert all(path.stat().st_size <= 1024 for path in files)
    assert sum(path.stat().st_size for path in files) <= 3072
    all_records = [item for path in files for item in records(path)]
    assert max(item["index"] for item in all_records) == 79
    assert min(item["index"] for item in all_records) > 0
    for item in all_records:
        validate_event(item)


def test_zero_backups_and_oversize_events_stay_bounded(tmp_path):
    store = JsonStore(tmp_path / "orc.jsonl", max_bytes=1024, backups=0)
    for _ in range(12):
        store.append(sample(payload="x" * MAX_EVENT_BYTES))
    assert store.path.stat().st_size <= 1024
    assert len(list(tmp_path.glob("orc.jsonl*"))) == 1
    assert all(item["truncated"] for item in records(store.path))


def test_concurrent_process_writers_survive_rotation(tmp_path):
    path = tmp_path / "orc.jsonl"
    # Spawn fresh interpreters; no inherited logging or lock state.
    context = multiprocessing.get_context("spawn")
    workers = [
        context.Process(target=write_process, args=(str(path), worker)) for worker in range(3)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=15)
        if worker.is_alive():
            worker.terminate()
            worker.join()
        assert worker.exitcode == 0
    items = [item for file in tmp_path.glob("orc.jsonl*") for item in records(file)]
    assert {(item["worker"], item["index"]) for item in items} == {
        (worker, index) for worker in range(3) for index in range(20)
    }
    assert len(items) == 60


def test_repeated_errors_summarize_suppression_but_distinct_operations_survive(
    tmp_path, monkeypatch
):
    now = [1.0]
    monkeypatch.setattr("common.logging.structured.time.monotonic", lambda: now[0])
    store = JsonStore(tmp_path / "orc.jsonl")
    failure = sample()
    failure.update(level="ERROR", event="broker.connection_failed")
    store.append(failure)
    store.append(failure)
    store.append(failure)
    now[0] = 7.0
    store.append(failure)
    assert records(store.path)[-1]["suppressed_count"] == 2
    for operation_id in ("one", "two"):
        store.append(dict(failure, operation_id=operation_id))
    assert len(records(store.path)) == 4


def test_nested_operation_context_is_restored():
    assert current_operation() is None
    with operation("outer"):
        with operation("inner"):
            assert current_operation() == "inner"
        assert current_operation() == "outer"
    assert current_operation() is None


def test_native_collection_preserves_identity_and_wraps_plain_output(tmp_path):
    item = sample(operation_id="route-17")
    item.update(component="map_renderer.routes", event="route.applied", pid=999)
    stream = io.StringIO(
        json.dumps(item) + "\nplain startup line\n" + "x" * (MAX_EVENT_BYTES * 2) + "\n"
    )
    store = JsonStore(tmp_path / "orc.jsonl")
    collect_native_output(stream, store, 999)
    collected = records(store.path)
    assert collected[0] == item
    assert collected[1]["event"] == "native.output"
    assert collected[2]["message"] == "Native log line exceeded size limit"
    assert all(record["pid"] == 999 for record in collected)
    assert stream.closed


def test_viewer_filters_and_follows_replacement_without_restart(tmp_path):
    path = tmp_path / "orc.jsonl"
    store = JsonStore(path)
    stop = threading.Event()
    seen_first = threading.Event()
    seen_second = threading.Event()
    seen = []

    def output(line):
        seen.append(line)
        if "First" in line:
            seen_first.set()
        if "Second" in line:
            seen_second.set()

    thread = threading.Thread(
        target=follow,
        kwargs={"path": path, "component": "navigation", "stop": stop, "output": output},
        daemon=True,
    )
    thread.start()
    try:
        store.append(sample())
        first = sample()
        first["message"] = "First"
        store.append(first)
        assert seen_first.wait(3)
        path.replace(tmp_path / "orc.jsonl.1")
        second = sample()
        second["message"] = "Second"
        ignored = dict(second, component="map_renderer.routes", message="Ignored")
        store.append(ignored)
        store.append(second)
        assert seen_second.wait(3)
        assert not any("Ignored" in line for line in seen)
    finally:
        stop.set()
        thread.join(timeout=3)
    assert not thread.is_alive()


def test_terminal_view_escapes_control_characters():
    item = sample()
    item.update(message="\x1b[31mred\nline", component="navigation\x1b[31m", event="event\nnext")
    assert "\x1b" not in readable(item) and "\n" not in readable(item)


def test_configure_is_idempotent_and_component_debug_is_collected(tmp_path, monkeypatch):
    root = logging.getLogger()
    original_handlers, original_level = list(root.handlers), root.level
    monkeypatch.setenv("ORC_LOG_DIR", str(tmp_path))
    monkeypatch.setenv("ORC_LOG_COMPONENT_LEVELS", "navigation.routing=DEBUG")
    monkeypatch.setenv("ORC_LOG_LEVEL", "INFO")
    try:
        configure_logging(stderr=False)
        store = configure_logging(stderr=False)
        assert sum(isinstance(handler, StoreHandler) for handler in root.handlers) == 1
        with operation("abc"):
            event(
                logging.getLogger("navigation.routing"),
                logging.DEBUG,
                "route.detail",
                "Route detail",
                point_count=10,
            )
        event(logging.getLogger("map_renderer.commands"), logging.DEBUG, "command.detail", "Hidden")
        assert len(records(store.path)) == 1
        assert records(store.path)[0]["operation_id"] == "abc"
        monkeypatch.setenv("ORC_LOG_COMPONENT_LEVELS", "")
        configure_logging(stderr=False)
        assert logging.getLogger("navigation.routing").level == logging.NOTSET
    finally:
        for handler in root.handlers:
            if handler not in original_handlers:
                handler.close()
        root.handlers[:] = original_handlers
        root.setLevel(original_level)


def test_viewer_drains_shutdown_events_and_respects_initial_offset(tmp_path):
    store = JsonStore(tmp_path / "orc.jsonl")
    store.append(sample())
    snapshot = store.path.stat()
    offset = (snapshot.st_ino, snapshot.st_size)
    final = sample()
    final["event"] = "app.stopped"
    store.append(final)
    stop = threading.Event()
    stop.set()
    seen = []
    follow(path=store.path, start_offset=offset, stop=stop, output=seen.append)
    assert len(seen) == 1 and "app.stopped" in seen[0]
