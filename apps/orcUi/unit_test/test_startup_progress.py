# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

from io import StringIO
from unittest.mock import Mock, patch

from apps.orcUi.main import StartupReporter


def test_startup_reporter_prints_stage_and_total_times_and_logs_milliseconds() -> None:
    output = StringIO()
    clock = Mock(side_effect=[11.25, 13.5])
    logger = Mock()
    reporter = StartupReporter(
        logger,
        started_at=10.0,
        output=output,
        clock=clock,
    )

    with patch("apps.orcUi.main.event") as log_event:
        reporter("core", "Core UI loaded")
        reporter("ready", "OpenRoadCode UI ready")

    lines = output.getvalue().splitlines()
    assert lines[0].startswith("[    1.250] Core UI loaded ")
    assert lines[0].endswith("(+1.250s)")
    assert "Core UI loaded ..." in lines[0]
    assert lines[1].startswith("[    3.500] OpenRoadCode UI ready ")
    assert lines[1].endswith("(+2.250s)")
    assert log_event.call_args_list[0].kwargs == {
        "stage": "core",
        "duration_ms": 1250,
        "elapsed_ms": 1250,
    }
    assert log_event.call_args_list[1].kwargs == {
        "stage": "ready",
        "duration_ms": 2250,
        "elapsed_ms": 3500,
    }
