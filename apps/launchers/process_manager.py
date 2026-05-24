import os
import signal
import subprocess
import time
from typing import Iterable, Optional


DEFAULT_DISPLAY_APP_PATTERNS = [
    "sdrpp",
    "sdr\\+\\+",
    "chromium",
    "chromium-browser",
    "streamlit",
]


PROTECTED_PROCESS_PATTERNS = [
    "vncserver",
    "tigervncserver",
    "Xtigervnc",
    "Xvnc",
    "xstartup",
    "openbox",
]


def _process_display(pid: int) -> Optional[str]:
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            env = f.read().split(b"\0")

        for item in env:
            if item.startswith(b"DISPLAY="):
                return item.decode(errors="ignore").split("=", 1)[1]

    except Exception:
        return None

    return None


def _process_cmdline(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            return f.read().replace(b"\0", b" ").decode(errors="ignore")
    except Exception:
        return ""


def _is_protected_process(cmdline: str) -> bool:
    return any(pattern in cmdline for pattern in PROTECTED_PROCESS_PATTERNS)


def close_display_apps(
    display: str = ":2",
    patterns: Optional[Iterable[str]] = None,
    delay_seconds: float = 0.5,
) -> None:
    patterns = list(patterns or DEFAULT_DISPLAY_APP_PATTERNS)

    for pattern in patterns:
        result = subprocess.run(
            ["pgrep", "-f", pattern],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )

        for pid_text in result.stdout.splitlines():
            if not pid_text.strip().isdigit():
                continue

            pid = int(pid_text.strip())
            cmdline = _process_cmdline(pid)

            if not cmdline:
                continue

            if _is_protected_process(cmdline):
                print(f"[*] Skipping protected process {pid}: {cmdline}")
                continue

            proc_display = _process_display(pid)

            if proc_display != display:
                print(
                    f"[*] Skipping pid {pid}; DISPLAY={proc_display}, "
                    f"wanted {display}: {cmdline}"
                )
                continue

            print(f"[*] Closing pid {pid} on DISPLAY={display}: {cmdline}")

            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    if delay_seconds > 0:
        time.sleep(delay_seconds)

def is_process_running(pattern: str) -> bool:
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def close_matching_display_apps(
    display: str,
    patterns: Iterable[str],
    delay_seconds: float = 0.0,
) -> None:
    close_display_apps(
        display=display,
        patterns=patterns,
        delay_seconds=delay_seconds,
    )

def kill_process_pattern(pattern: str) -> None:
    subprocess.run(
        ["pkill", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
