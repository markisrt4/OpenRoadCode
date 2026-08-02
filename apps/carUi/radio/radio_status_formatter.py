from __future__ import annotations

from controllers.radio.radio_types import RadioPreset


def format_frequency(frequency_hz: int, precision: int = 1) -> str:
    """Format a frequency using an appropriate Hz, kHz, or MHz unit."""
    if frequency_hz >= 1_000_000:
        value = frequency_hz / 1_000_000
        return f"{value:.{precision}f} MHz"

    if frequency_hz >= 1_000:
        value = frequency_hz / 1_000
        return f"{value:.1f} kHz"

    return f"{frequency_hz} Hz"


def compact_preset_label(
    preset: RadioPreset,
    precision: int = 1,
) -> str:
    """Return a compact numeric frequency for MHz presets, else its label."""
    if preset.frequency_hz >= 1_000_000:
        value = preset.frequency_hz / 1_000_000
        return f"{value:.{precision}f}"

    return preset.label


def format_step(step_hz: int) -> str:
    """Format a tuning step using an appropriate frequency unit."""
    if step_hz >= 1_000_000:
        return f"{step_hz / 1_000_000:g} MHz"

    if step_hz >= 1_000:
        return f"{step_hz / 1_000:g} kHz"

    return f"{step_hz:g} Hz"
