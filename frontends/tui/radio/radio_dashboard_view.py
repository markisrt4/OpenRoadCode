"""Reusable curses presentation for radio tuning."""

import curses
from collections.abc import Sequence
from typing import Protocol

from frontends.tui.curses_helpers import addstr


class PresetSnapshot(Protocol):
    """Minimum preset data required by the terminal view."""

    label: str
    frequency_hz: int


class RadioDashboardView:
    """Render radio categories, tuning state, and presets."""

    def render(
        self,
        screen,
        *,
        labels: Sequence[str],
        selected_index: int,
        frequency_hz: int | None,
        mode_name: str,
        presets: Sequence[PresetSnapshot],
        selected_preset_index: int | None,
        started: bool,
        status: str,
        signal_strength: float | str | None = None,
        snr: float | str | None = None,
        rds: str | None = None,
    ) -> None:
        """Draw one complete receiver screen."""
        screen.erase()
        height, width = screen.getmaxyx()
        addstr(screen, 0, 2, "OpenRoadCode Radio", curses.A_BOLD)
        addstr(screen, 1, 0, "─" * max(0, width - 1))

        column = 2
        for index, label in enumerate(labels):
            text = f" {index + 1}:{label} "
            attr = curses.A_REVERSE | curses.A_BOLD if index == selected_index else 0
            addstr(screen, 2, column, text, attr)
            column += len(text) + 1

        power = "ON" if started else "OFF"
        addstr(screen, 4, 3, f"Receiver {power}", curses.A_BOLD)
        frequency = format_frequency(frequency_hz) if frequency_hz else "--"
        addstr(screen, 6, 3, frequency, curses.A_BOLD)
        addstr(screen, 7, 3, f"Mode: {mode_name or '--'}")
        addstr(screen, 9, 3, f"Signal: {_value(signal_strength)}")
        addstr(screen, 10, 3, f"SNR:    {_value(snr)}")
        addstr(screen, 11, 3, f"RDS:    {rds or '--'}")

        preset_column = max(34, width // 2)
        addstr(screen, 4, preset_column, "Presets", curses.A_BOLD)
        for index, preset in enumerate(presets[: max(0, height - 9)]):
            marker = ">" if index == selected_preset_index else " "
            addstr(
                screen,
                6 + index,
                preset_column,
                f"{marker} {preset.label:<20} {format_frequency(preset.frequency_hz)}",
            )

        addstr(screen, height - 3, 0, "─" * max(0, width - 1))
        addstr(screen, height - 2, 2, status)
        controls = "1-4: band  p: power  ←/→: tune  [/]: preset  b: back  q: quit"
        addstr(screen, height - 1, 2, controls)
        screen.refresh()


def _value(value: float | str | None) -> str:
    return "--" if value is None else str(value)


def format_frequency(frequency_hz: int) -> str:
    """Format hertz using a compact terminal-friendly unit."""
    if frequency_hz >= 1_000_000:
        value = f"{frequency_hz / 1_000_000:.3f}".rstrip("0").rstrip(".")
        return f"{value} MHz"
    if frequency_hz >= 1_000:
        value = f"{frequency_hz / 1_000:.3f}".rstrip("0").rstrip(".")
        return f"{value} kHz"
    return f"{frequency_hz} Hz"
