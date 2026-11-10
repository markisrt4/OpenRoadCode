# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import os
import signal
import subprocess
import time
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from common.logging.lifecycle import logged_action
from common.logging.structured import event

LOGGER = logging.getLogger("runtime.processes")


def _child_context(process, *args, **kwargs):
    return {"child_pid": process.pid if type(process.pid) is int else None}


DEFAULT_DISPLAY_APP_PATTERNS = (
    "sdrpp",
    "sdr\\+\\+",
    "chromium",
    "chromium-browser",
    "streamlit",
)

PROTECTED_PROCESS_PATTERNS = (
    "vncserver",
    "tigervncserver",
    "Xtigervnc",
    "Xvnc",
    "xstartup",
    "openbox",
)


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """Describe a matching operating-system process."""

    pid: int
    command_line: str
    display: str | None


def find_matching_processes(pattern: str) -> tuple[ProcessInfo, ...]:
    """Find processes whose command line matches a ``pgrep`` pattern.

    @param pattern Extended regular expression matched against command lines.
    @return Matching process metadata.
    """
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    matches: list[ProcessInfo] = []
    for pid_text in result.stdout.splitlines():
        if not pid_text.strip().isdigit():
            continue

        pid = int(pid_text)
        command_line = _process_command_line(pid)
        if not command_line:
            continue

        matches.append(
            ProcessInfo(
                pid=pid,
                command_line=command_line,
                display=_process_display(pid),
            )
        )

    return tuple(matches)


def is_process_running(pattern: str) -> bool:
    """Return whether any process command line matches ``pattern``."""
    return bool(find_matching_processes(pattern))


@logged_action("runtime.processes", "process.action", "terminate", context=_child_context)
def terminate_process(
    process: subprocess.Popen[bytes] | subprocess.Popen[str],
    *,
    timeout_seconds: float = 5.0,
) -> None:
    """Terminate a child process group, escalating to SIGKILL on timeout.

    @param process Child process whose process group should be terminated.
    @param timeout_seconds Grace period before forced termination.
    """
    if process.poll() is not None:
        code = process.wait()
        event(
            LOGGER,
            logging.INFO,
            "process.exit_observed",
            "Child process exit observed",
            exit_code=code if type(code) is int else None,
            **_child_context(process),
        )
        return

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        event(
            LOGGER,
            logging.WARNING,
            "process.kill_forced",
            "Child exceeded termination grace period",
            **_child_context(process),
        )
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        code = process.wait(timeout=timeout_seconds)
    except ProcessLookupError:
        code = process.wait()
    event(
        LOGGER,
        logging.INFO,
        "process.exit_observed",
        "Child process exit observed",
        exit_code=code if type(code) is int else None,
        **_child_context(process),
    )


@logged_action("runtime.processes", "process.action", "close_display_apps")
def close_display_apps(
    display: str,
    patterns: Iterable[str] = DEFAULT_DISPLAY_APP_PATTERNS,
    *,
    delay_seconds: float = 0.0,
) -> None:
    """Terminate matching applications running on a specific X display.

    Protected desktop and VNC processes are never terminated.

    @param display Exact ``DISPLAY`` environment value to match.
    @param patterns Command-line patterns identifying applications.
    @param delay_seconds Optional delay after sending termination signals.
    """
    for pattern in patterns:
        for process in find_matching_processes(pattern):
            if _is_protected_process(process.command_line):
                continue
            if process.display != display:
                continue

            try:
                os.kill(process.pid, signal.SIGTERM)
                event(
                    LOGGER,
                    logging.INFO,
                    "process.signal_sent",
                    "Display application termination requested",
                    child_pid=process.pid,
                )
            except ProcessLookupError:
                pass

    if delay_seconds > 0:
        time.sleep(delay_seconds)


def close_matching_display_apps(
    display: str,
    patterns: Iterable[str],
    *,
    delay_seconds: float = 0.0,
) -> None:
    """Close display applications using an explicit set of patterns.

    @param display Exact ``DISPLAY`` environment value to match.
    @param patterns Command-line patterns identifying applications.
    @param delay_seconds Optional delay after sending termination signals.
    """
    close_display_apps(
        display=display,
        patterns=patterns,
        delay_seconds=delay_seconds,
    )


def _process_display(pid: int) -> str | None:
    try:
        data = Path(f"/proc/{pid}/environ").read_bytes()
    except (OSError, PermissionError):
        return None

    for item in data.split(b"\0"):
        if item.startswith(b"DISPLAY="):
            return item.decode(errors="ignore").split("=", 1)[1]

    return None


def _process_command_line(pid: int) -> str:
    try:
        return (
            Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        )
    except (OSError, PermissionError):
        return ""


def _is_protected_process(command_line: str) -> bool:
    return any(pattern in command_line for pattern in PROTECTED_PROCESS_PATTERNS)
