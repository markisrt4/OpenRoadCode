"""Keyboard hardware contracts and optional Linux implementation."""

from importlib import import_module
from typing import Any

from hardware_io.keyboard.keyboard_reader_if import KeyboardReaderIf, KeyCallback

__all__ = ["KeyboardReader", "KeyboardReaderIf", "KeyCallback"]


def __getattr__(name: str) -> Any:
    """Load the evdev-backed implementation only when explicitly requested."""
    if name != "KeyboardReader":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = import_module(
        "hardware_io.keyboard.keyboard_reader"
    ).KeyboardReader
    globals()[name] = value
    return value
