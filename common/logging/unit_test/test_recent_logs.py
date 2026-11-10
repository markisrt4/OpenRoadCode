# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Log paging and authenticated handler contracts without host sockets."""

from io import BytesIO
from http import HTTPStatus
import json
import os
from unittest.mock import Mock, patch

import pytest

from common.logging.recent import MAX_EVENTS, SCAN_BYTES, read_recent
from common.logging.structured import JsonStore
from services.common.service_manager_logs import serve_logs
from services.linux.systemd_service_manager_http import SystemdServiceManagerHandler
from services.termux.service_manager_http import ServiceManagerHandler


def record(number=0, **fields):
    return dict(
        timestamp="2026-10-04T12:00:00.000Z",
        level="INFO",
        component="runtime.apps",
        event="app.started",
        message=f"App {number}",
        pid=123,
        **fields,
    )


def write(path, *items):
    with path.open("ab") as stream:
        for item in items:
            stream.write((json.dumps(item) + "\n").encode())


def test_recent_history_is_bounded_and_live_pages_do_not_repeat(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, *(record(i) for i in range(400)))
    page = read_recent(path=path)
    assert len(page["events"]) == MAX_EVENTS
    assert page["events"][0]["message"] == "App 200"
    assert read_recent(path=path, cursor=page["cursor"])["events"] == []
    write(path, record(400))
    assert read_recent(path=path, cursor=page["cursor"])["events"] == [record(400)]


def test_live_backlog_is_paged_without_loss(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, record())
    cursor = read_recent(path=path)["cursor"]
    write(path, *(record(i) for i in range(1, 502)))
    events = []
    while True:
        page = read_recent(path=path, cursor=cursor)
        events.extend(page["events"])
        cursor = page["cursor"]
        if not page["has_more"]:
            break
    assert events == [record(i) for i in range(1, 502)]


def test_follow_retained_rotations(tmp_path):
    path = tmp_path / "orc.jsonl"
    store = JsonStore(path, max_bytes=1024)
    store.append(record())
    cursor = read_recent(path=path)["cursor"]
    items = [record(i, padding="x" * 250) for i in range(1, 6)]
    for item in items:
        store.append(item)
    page = read_recent(path=path, cursor=cursor)
    assert page["events"] == items
    assert not page["reset"]
    assert read_recent(path=path)["events"] == [record(), *items]


def test_scan_budget_does_not_drop_a_record_crossing_the_page_boundary(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, record())
    cursor = read_recent(path=path)["cursor"]
    items = [record(i, padding="x" * 5000) for i in range(1, 101)]
    write(path, *items)
    events = []
    for _ in range(5):
        page = read_recent(path=path, cursor=cursor)
        events.extend(page["events"])
        cursor = page["cursor"]
        if not page["has_more"]:
            break
    assert events == items


def test_unmatched_pages_advance_and_component_filter_matches_only_dotted_prefix(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, dict(record(), component="runtimeOther"), record(1))
    page = read_recent(path=path, component="runtime")
    assert page["events"] == [record(1)]
    write(path, record(2))
    filtered = read_recent(path=path, cursor=page["cursor"], level="ERROR")
    assert filtered["events"] == []
    assert filtered["cursor"] != page["cursor"]


def test_expired_and_truncated_cursors_reset_to_recent_history(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, record(1000))
    old = read_recent(path=path)["cursor"]
    path.write_text("")
    write(path, record(1))
    assert read_recent(path=path, cursor=old)["reset"]
    path.unlink()
    write(path, record(2))
    page = read_recent(path=path, cursor="0:0:0:0")
    assert page["reset"] and page["events"] == [record(2)]


def test_filters_skip_invalid_records_and_never_advance_past_partial_line(tmp_path):
    path = tmp_path / "orc.jsonl"
    path.write_bytes(b"not json\n{}\n")
    write(path, record(), dict(record(1), level="ERROR", component="media.player"))
    page = read_recent(path=path, level="ERROR", component="media")
    assert len(page["events"]) == 1
    encoded = json.dumps(record(2)).encode()
    with path.open("ab") as stream:
        stream.write(encoded[:40])
    partial = read_recent(path=path, cursor=page["cursor"])
    assert partial["cursor"] == page["cursor"]
    with path.open("ab") as stream:
        stream.write(encoded[40:] + b"\n")
    assert read_recent(path=path, cursor=partial["cursor"])["events"] == [record(2)]


def test_oversized_line_does_not_stall_or_parse_its_suffix(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, record())
    cursor = read_recent(path=path)["cursor"]
    with path.open("ab") as stream:
        stream.write(b"x" * (SCAN_BYTES * 2) + json.dumps(record(99)).encode() + b"\n")
    write(path, record(1))
    events = []
    for _ in range(4):
        page = read_recent(path=path, cursor=cursor)
        cursor = page["cursor"]
        events += page["events"]
    assert events == [record(1)]


@pytest.mark.parametrize(
    "cursor", ["/etc/passwd", "1:2:-1:0", "1:2:3:2", "9" * 500, "1:2:99999999999999999999:0"]
)
def test_invalid_cursor_is_rejected(tmp_path, cursor):
    with pytest.raises(ValueError):
        read_recent(path=tmp_path / "orc.jsonl", cursor=cursor)


def test_missing_store_is_empty_without_creating_directories(tmp_path):
    path = tmp_path / "missing" / "orc.jsonl"
    assert read_recent(path=path)["events"] == []
    assert not path.parent.exists()


@pytest.mark.parametrize("handler_class", [ServiceManagerHandler, SystemdServiceManagerHandler])
@pytest.mark.parametrize("accepted", [False, True])
def test_handlers_authenticate_before_reading_logs(handler_class, accepted):
    handler = object.__new__(handler_class)
    handler.path = "/logs?level=ERROR"
    handler._authenticate = Mock(return_value=accepted)
    handler._json = Mock()
    with patch(
        "services.common.service_manager_logs.read_recent", return_value={"events": []}
    ) as read:
        handler.do_GET()
    if accepted:
        read.assert_called_once_with(cursor="", level="ERROR", component="")
        assert handler._json.call_args.args[0] == 200
    else:
        read.assert_not_called()


@pytest.mark.parametrize("handler_class", [ServiceManagerHandler, SystemdServiceManagerHandler])
@pytest.mark.parametrize(
    "token,expected",
    [(None, 401), ("wrong", 401), ("admin", 200), ("paired", 200), ("revoked", 401)],
)
def test_log_endpoint_uses_existing_admin_and_pairing_policy(handler_class, token, expected):
    handler = object.__new__(handler_class)
    handler.path = "/logs"
    handler.client_address = ("192.0.2.10", 12345)
    handler.headers = {"Authorization": f"Bearer {token}"} if token else {}
    handler.auth_token = "admin"
    handler.pairing = Mock()
    handler.pairing.authorized.side_effect = lambda value: value == "paired"
    handler._json = Mock()
    with patch(
        "services.common.service_manager_logs.read_recent", return_value={"events": []}
    ) as read:
        handler.do_GET()
    assert handler._json.call_args.args[0] == expected
    assert read.called == (expected == 200)


def test_termux_keeps_existing_same_phone_access_policy():
    handler = object.__new__(ServiceManagerHandler)
    handler.path = "/logs"
    handler.client_address = ("127.0.0.1", 12345)
    handler.headers = {}
    handler.auth_token = "admin"
    handler._json = Mock()
    with patch("services.common.service_manager_logs.read_recent", return_value={"events": []}):
        handler.do_GET()
    assert handler._json.call_args.args[0] == 200


@pytest.mark.parametrize(
    "query",
    [
        "?path=/etc/passwd",
        "?level=NOPE",
        "?cursor=nope",
        "?level=INFO&level=ERROR",
        "?component=../../secret",
        "?a=1&b=2&c=3&d=4",
    ],
)
def test_endpoint_rejects_bad_queries_without_echoing_values(query):
    handler = Mock(path="/logs" + query)
    serve_logs(handler, scope="Shared ORC log store")
    handler._json.assert_called_once_with(400, {"error": "Invalid log query"})


def test_endpoint_handles_permission_error_without_disclosing_path():
    handler = Mock(path="/logs")
    with patch(
        "services.common.service_manager_logs.read_recent",
        side_effect=PermissionError("/private/path"),
    ):
        serve_logs(handler, scope="test")
    handler._json.assert_called_once_with(503, {"error": "Log store unavailable"})


def test_response_is_json_and_disables_caching():
    handler = object.__new__(ServiceManagerHandler)
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.wfile = BytesIO()
    handler._json(HTTPStatus.OK, {"events": [record()]})
    handler.send_header.assert_any_call("Cache-Control", "no-store")
    assert json.loads(handler.wfile.getvalue())["events"] == [record()]


def test_endpoint_uses_only_server_configured_store(tmp_path):
    path = tmp_path / "orc.jsonl"
    write(path, record())
    handler = Mock(path="/logs")
    with patch.dict(os.environ, {"ORC_LOG_DIR": str(tmp_path)}):
        serve_logs(handler, scope="Shared ORC log store")
    assert handler._json.call_args.args[1]["events"] == [record()]
