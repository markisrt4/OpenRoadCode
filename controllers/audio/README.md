# Audio Controller

The `audio` controller provides a common interface for controlling system audio output.

Audio applications and input components can use the audio controller without depending directly on a specific operating system audio implementation.

## Components

| Component | Description |
|-----------|-------------|
| `AudioControllerIf` | Defines the common audio control interface. |
| `PipewireAudioController` | Controls PipeWire audio output using `wpctl`. |

## Directory Layout

```text
audio/
├── __init__.py
├── audio_controller_if.py
├── pipewire_audio_controller.py
├── README.md
└── component_test/
    ├── __init__.py
    └── audio_cli.py
```

## Features

The audio controller provides:

- Volume increase
- Volume decrease
- Discrete volume levels
- Direct volume level selection
- Relative volume adjustment
- Replaceable audio controller implementations

## Audio Controller Interface

`AudioControllerIf` defines the common audio control interface.

Implementations provide:

```python
maximum_level
volume_up()
volume_down()
get_volume_level()
set_volume_level(level)
adjust_volume(steps)
is_muted()
toggle_mute()
```

Higher-level components should depend on `AudioControllerIf` rather than a specific audio implementation.

Example:

```python
from controllers.audio import AudioControllerIf


def adjust_output_volume(
    controller: AudioControllerIf,
    steps: int,
) -> None:
    controller.adjust_volume(steps)
```

## PipeWire Audio Controller

`PipewireAudioController` controls the default PipeWire audio sink using `wpctl`.

The controller operates on:

```text
@DEFAULT_AUDIO_SINK@
```

This allows the operating system to determine the active audio output device.
Relative volume increases pass a `1.0` limit to `wpctl`, preventing software
amplification above 100%.

Example:

```python
from controllers.audio import PipewireAudioController


controller = PipewireAudioController()

controller.volume_up()
controller.volume_down()

level = controller.get_volume_level()

controller.set_volume_level(10)
```

## Volume Levels

The PipeWire controller exposes system volume as discrete levels.

By default:

```text
steps = 20
step_percent = 5
```

This produces levels from:

```text
0 through 20
```

where:

```text
0  = 0%
1  = 5%
2  = 10%
...
20 = 100%
```

Volume-up operations clamp at 100%; further clockwise encoder steps leave the
system at level `20` rather than enabling PipeWire amplification.

Mute is controlled with `wpctl set-mute ... toggle`. `toggle_mute()` returns the
resulting state so application widgets can update immediately.

The number of levels can be configured:

```python
controller = PipewireAudioController(
    steps=10,
    step_percent=10,
)
```

## Relative Volume Adjustment

`adjust_volume()` changes the current volume by a number of discrete steps.

Example:

```python
controller.adjust_volume(1)
```

Increase volume by one level.

```python
controller.adjust_volume(-1)
```

Decrease volume by one level.

Multiple steps may be applied at once:

```python
controller.adjust_volume(3)
controller.adjust_volume(-4)
```

This is useful for input devices that report relative movement, such as rotary encoders.

Example:

```python
def volume_rotated(turns: int) -> None:
    audio_controller.adjust_volume(turns)
```

## Dependencies

The PipeWire implementation requires `wpctl`.

Verify that `wpctl` is available:

```bash
wpctl --version
```

The active audio sink can be inspected using:

```bash
wpctl status
```

Current volume can be read using:

```bash
wpctl get-volume @DEFAULT_AUDIO_SINK@
```

## Component Test

A CLI component test is provided.

Run from the project root:

```bash
python3 -m controllers.audio.component_test.audio_cli
```

Available commands:

```text
+          Volume up
-          Volume down
s <level>  Set volume level
g          Get volume level
q          Quit
```

Example session:

```text
audio> g
Volume level: 8

audio> +
Volume level: 9

audio> s 12
Volume level: 12

audio> -
Volume level: 11
```

## Car UI Volume Encoder Integration

The Car UI reserves one configured rotary encoder for global system volume.
The input router depends on `RotaryEncoderIf` and invokes the audio controller's
`volume_up()` or `volume_down()` operation for each signed encoder step:

```text
RotaryEncoderIf
        |
        v
EncoderEventRouter
        |
        v
AudioControllerIf
        |
        v
PipewireAudioController
```

The encoder driver and volume device index are configured in
`apps/carUi/config/car_ui_runtime.toml`. Neither `AudioControllerIf` nor
`PipewireAudioController` depends on Seesaw addresses or GPIO pins.

Test the real configured volume knob and default PipeWire sink with:

```bash
python3 -m apps.carUi.input.component_test.volume_encoder_cli
```

This test starts only the configured volume device. Other configured encoders
may be disconnected without preventing the volume test from running.
It reports 20 levels by default, matching the controller's 5% PipeWire step.
The Car UI theme's eight volume bars are a visual scale rather than the audio
controller's native resolution.

`VolumeManager` maps the controller range proportionally onto that visual
scale:

```text
Audio level  0/20  -> 0 bars
Audio level  5/20  -> 2 bars
Audio level 10/20  -> 4 bars
Audio level 15/20  -> 6 bars
Audio level 20/20  -> 8 bars
```

Positive nonzero audio levels display at least one bar. Encoder events and
top-bar volume buttons use the same mapping.

Pressing the configured volume encoder calls `AudioControllerIf.toggle_mute()`.
While muted, the top bar renders all eight bars in red. The underlying volume
level is retained and displayed again when the encoder is pressed to unmute.

## Design

The audio controller represents system audio control behavior.

Higher-level components interact with `AudioControllerIf` and do not need to know how system volume is controlled.

Concrete implementations are responsible for interacting with the underlying audio system.

For example:

```text
Input Device
     |
     v
AudioControllerIf
     |
     v
PipewireAudioController
     |
     v
wpctl
     |
     v
PipeWire
```

This allows additional audio controller implementations to be added without changing components that use audio control.

Possible implementations may include:

- PipeWire
- PulseAudio
- ALSA
- Remote audio services
- Mock audio controllers

Operating system and audio-system-specific behavior remains inside the concrete audio controller implementation.
