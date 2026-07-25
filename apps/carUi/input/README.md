# Car UI Input Routing

The Car UI input layer converts generic rotary encoder callbacks into
application events on the UI thread.

## Architecture

```text
car_ui_runtime.toml
        |
        v
Rotary encoder runtime factory
        |
        v
RotaryEncoderIf instances
        |
        v
EncoderEventRouter
        |
        +-- configured volume index -> AudioControllerIf
        |
        +-- contextual slots -> active panel callbacks
```

`EncoderEventRouter` depends only on `RotaryEncoderIf`. It does not know whether
an encoder uses Seesaw/I2C, Raspberry Pi GPIO, or another future implementation.

## Encoder identity

The configured `volume_index` selects one device for global system-volume
control. Its rotation is never forwarded to a panel. Pressing its button
toggles system mute; releasing it has no additional action.

Remaining devices are exposed to the active panel as zero-based contextual
slots in configured device order. Both button callbacks identify their source:

```python
def rotated(slot: int, steps: int) -> None:
    ...

def button_pressed(slot: int) -> None:
    ...

def button_released(slot: int) -> None:
    ...
```

Panel transitions clear the previous callbacks. Events queued under an older
panel generation are discarded rather than delivered to the newly active
panel.

## Threading

Hardware callbacks enqueue events. The router drains the queue from the UI
scheduler, ensuring that panel and volume callbacks execute on the UI thread.
The same scheduler calls `RotaryEncoderIf.poll()`, allowing accumulated GPIO
events and callback-driven Seesaw events to share one interface.

## System volume component test

Run:

```bash
python3 -m apps.carUi.input.component_test.volume_encoder_cli
```

This loads the production TOML but constructs and starts only the device
selected by `volume_index`. Contextual devices are intentionally not started,
so a disconnected panel encoder cannot prevent testing the volume knob.

The test changes the actual default PipeWire sink volume and prints the
resulting level after each rotation step. It requires `wpctl` and the configured
volume encoder hardware. It reports 20 levels by default, matching the default
5% PipeWire increment; the Car UI's eight bars are only a visual indicator.
The PipeWire controller limits positive adjustments to 100%.

The production `VolumeManager` maps the 20-level audio range proportionally to
the top bar's eight segments. For example, levels `5`, `10`, `15`, and `20`
display two, four, six, and eight bars respectively. While muted, all bars are
rendered in red so mute is distinguishable from volume zero.

## Automated tests

```bash
python3 -m unittest \
    apps.carUi.input.component_test.test_encoder_event_router \
    apps.carUi.input.component_test.test_volume_encoder_cli
```
