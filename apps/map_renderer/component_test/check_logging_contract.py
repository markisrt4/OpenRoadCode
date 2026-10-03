# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Validate actual C++ output against the shared ORC logging schema."""

import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from common.logging.structured import validate_event


def check(executable, level, overrides, expected):
    environment = dict(os.environ, ORC_LOG_LEVEL=level, ORC_LOG_COMPONENT_LEVELS=overrides)
    result = subprocess.run(
        [executable],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=10,
    )
    if result.stdout:
        raise AssertionError("Native logger must write to stderr")
    items = [json.loads(line) for line in result.stderr.splitlines()]
    if [(item["component"], item["level"]) for item in items] != expected:
        raise AssertionError(f"Unexpected level filtering: {items}")
    for item in items:
        validate_event(item)
        if item["component"] == "map_renderer.routes":
            assert item["operation_id"] == "route-17"
            assert item["command"] == "set_route"
            assert item["message"] == 'Route "accepted"\nnext line: café'


def main():
    executable = sys.argv[1]
    routes = "map_renderer.routes"
    commands = "map_renderer.commands"
    levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    check(executable, "INFO", "", [(routes, level) for level in levels[1:]] + [(commands, "INFO")])
    check(executable, "DEBUG", "", [(routes, level) for level in levels] + [(commands, "INFO")])
    check(executable, "CRITICAL", "", [(routes, "CRITICAL")])
    check(
        executable,
        "INFO",
        "map_renderer=ERROR,map_renderer.routes=DEBUG",
        [(routes, level) for level in levels],
    )
    print("Native logging schema, escaping, correlation and filtering passed")


if __name__ == "__main__":
    main()
