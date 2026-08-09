from importlib import import_module
from typing import TYPE_CHECKING, Any

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
)
from controllers.input.input_mapper import (
    InputMapper,
)
from controllers.input.input_manager import InputManager
from controllers.input.push_button_input_adapter import PushButtonInputAdapter

if TYPE_CHECKING:
    from controllers.input.keyboard_input_adapter import KeyboardInputAdapter
    from controllers.input.rotary_encoder_input_adapter import (
        RotaryEncoderInputAdapter,
    )

__all__ = [
    "InputMapper",
    "InputDeviceId",
    "InputDeviceType",
    "InputEvent",
    "InputEventType",
    "InputManager",
    "KeyboardInputAdapter",
    "PushButtonInputAdapter",
    "RotaryEncoderInputAdapter",
]


def __getattr__(name: str) -> Any:
    """Load adapters only when requested so optional hardware stays optional."""

    adapter_modules = {
        "KeyboardInputAdapter": "controllers.input.keyboard_input_adapter",
        "RotaryEncoderInputAdapter": (
            "controllers.input.rotary_encoder_input_adapter"
        ),
    }
    module_name = adapter_modules.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
