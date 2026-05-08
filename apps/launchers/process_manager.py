import subprocess
import time
from typing import Iterable, Optional


DEFAULT_DISPLAY_APP_PATTERNS = [
    "chromium",
    "chromium-browser",
    "sdrpp",
    "sdr++",
]


def is_process_running(pattern: str) -> bool:
    result = subprocess.run(
        ["pgrep", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def kill_process_pattern(pattern: str) -> None:
    subprocess.run(
        ["pkill", "-f", pattern],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def kill_process_patterns(patterns: Iterable[str]) -> None:
    for pattern in patterns:
        kill_process_pattern(pattern)


def close_display_apps(
    display: str = ":2",
    patterns: Optional[Iterable[str]] = None,
    delay_seconds: float = 0.5,
) -> None:
    for pattern in patterns or DEFAULT_DISPLAY_APP_PATTERNS:
        # Only kill processes on the target DISPLAY
        subprocess.run(
            f'DISPLAY={display} pkill -f "{pattern}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    if delay_seconds > 0:
        time.sleep(delay_seconds)
