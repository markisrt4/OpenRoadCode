# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Shared read-only log endpoint; callers authenticate before dispatch."""

from http import HTTPStatus
from urllib.parse import parse_qs, urlsplit

from common.logging.recent import read_recent


def serve_logs(handler, *, scope: str) -> None:
    try:
        if len(handler.path) > 2048:
            raise ValueError("Log query too long")
        query = parse_qs(urlsplit(handler.path).query, keep_blank_values=True, max_num_fields=3)
        if set(query) - {"cursor", "level", "component"} or any(
            len(v) != 1 for v in query.values()
        ):
            raise ValueError("Invalid log query")
        page = read_recent(
            cursor=query.get("cursor", [""])[0],
            level=query.get("level", ["INFO"])[0],
            component=query.get("component", [""])[0],
        )
    except ValueError:
        handler._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid log query"})
        return
    except OSError:
        handler._json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "Log store unavailable"})
        return
    handler._json(HTTPStatus.OK, dict(page, scope=scope))
