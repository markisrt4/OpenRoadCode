"""Component test for mapping and dispatching mocked input events."""

from __future__ import annotations

from dataclasses import dataclass, field

from input_events import (
    InputDeviceId,
    InputDeviceType,
    InputEvent,
    InputEventType,
)
from controllers.input.input_manager import InputManager
from controllers.input.input_mapper import InputMapper
from ui.ui_action import UiAction
from ui.ui_event_handler_if import UiEventHandlerIf


@dataclass
class MockUiEventHandler(UiEventHandlerIf):
    """Capture actions dispatched by InputManager."""

    actions: list[UiAction] = field(default_factory=list)

    def handle_ui_action(
        self,
        action: UiAction,
    ) -> None:
        self.actions.append(action)
        print(f"UI action: {action.name}")


def main() -> int:
    keyboard_id = InputDeviceId(
        device_type=InputDeviceType.KEYBOARD,
        instance=0,
    )

    user_encoder_id = InputDeviceId(
        device_type=InputDeviceType.ROTARY_ENCODER,
        instance=0,
    )

    volume_encoder_id = InputDeviceId(
        device_type=InputDeviceType.ROTARY_ENCODER,
        instance=1,
    )

    ui_handler = MockUiEventHandler()

    mapper = InputMapper(
        user_encoder_id=user_encoder_id,
        volume_encoder_id=volume_encoder_id,
    )

    input_manager = InputManager(
        mapper=mapper,
        ui_handler=ui_handler,
    )

    events = [
        InputEvent(
            device_id=keyboard_id,
            event_type=InputEventType.BUTTON_PRESSED,
            value="KEY_UP",
        ),
        InputEvent(
            device_id=keyboard_id,
            event_type=InputEventType.BUTTON_PRESSED,
            value="KEY_DOWN",
        ),
        InputEvent(
            device_id=keyboard_id,
            event_type=InputEventType.BUTTON_PRESSED,
            value="KEY_ENTER",
        ),
        InputEvent(
            device_id=keyboard_id,
            event_type=InputEventType.BUTTON_PRESSED,
            value="KEY_ESC",
        ),
        InputEvent(
            device_id=keyboard_id,
            event_type=InputEventType.BUTTON_PRESSED,
            value="KEY_HOME",
        ),
        InputEvent(
            device_id=user_encoder_id,
            event_type=InputEventType.ROTATED,
            value=1,
        ),
        InputEvent(
            device_id=user_encoder_id,
            event_type=InputEventType.ROTATED,
            value=-1,
        ),
        InputEvent(
            device_id=user_encoder_id,
            event_type=InputEventType.BUTTON_PRESSED,
        ),
        InputEvent(
            device_id=user_encoder_id,
            event_type=InputEventType.BUTTON_RELEASED,
        ),
        InputEvent(
            device_id=volume_encoder_id,
            event_type=InputEventType.ROTATED,
            value=1,
        ),
        InputEvent(
            device_id=volume_encoder_id,
            event_type=InputEventType.ROTATED,
            value=-1,
        ),
        InputEvent(
            device_id=volume_encoder_id,
            event_type=InputEventType.BUTTON_PRESSED,
        ),
    ]

    for event in events:
        input_manager.handle_input_event(event)

    expected_actions = [
        UiAction.NAVIGATE_UP,
        UiAction.NAVIGATE_DOWN,
        UiAction.SELECT,
        UiAction.BACK,
        UiAction.HOME,
        UiAction.NAVIGATE_DOWN,
        UiAction.NAVIGATE_UP,
        UiAction.SELECT,
        UiAction.VOLUME_UP,
        UiAction.VOLUME_DOWN,
        UiAction.VOLUME_MUTE,
    ]

    assert ui_handler.actions == expected_actions

    print()
    print("Mock input event component test passed.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
