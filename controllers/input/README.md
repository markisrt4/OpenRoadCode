# Input Controller Layer

This package translates physical input into semantic UI actions.

## Layer boundaries

```text
hardware_io driver
    -> device-specific callback
input adapter
    -> generic InputEvent
InputManager + InputMapperIf
    -> UiAction
UiEventHandlerIf
    -> concrete UI behavior
```

## Responsibilities

- `InputDeviceId` identifies a physical input without using string IDs.
- `InputEvent` describes what physically happened.
- Input adapters translate device callbacks into `InputEvent`.
- `ConfigurableInputMapper` maps events to `UiAction`.
- `InputManager` delivers mapped actions to `UiEventHandlerIf`.
- The concrete UI decides how an action affects the current screen.

## Rotary encoder instances

A suggested assignment is:

- Rotary encoder instance 0: dedicated volume knob
- Rotary encoder instance 1: user-configurable knob 1
- Rotary encoder instance 2: user-configurable knob 2

The adapter does not know these meanings. Bindings assign the behavior.

## Touchscreen and mouse events

A touchscreen widget callback often already knows its semantic action. It may call:

```python
input_manager.dispatch_ui_action(UiAction.HOME)
```

Raw gestures or pointer events that require mapping can instead be represented as
generic `InputEvent` values and handled through the mapper.
