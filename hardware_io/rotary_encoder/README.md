# Rotary Encoder

The `rotary_encoder` component provides a common interface for receiving rotary encoder events.

Two rotary encoder implementations are provided:

- `GpioRotaryEncoder`
- `SeesawRotaryEncoder`

Both implementations use the `RotaryEncoder` interface and report rotation and button events using callbacks.

## Rotary Encoder Interface

The `RotaryEncoder` interface reports the following events:

- Rotation
- Button pressed
- Button released

Rotation callbacks receive the number of encoder steps.

```python
def rotated(steps: int) -> None:
    print(f"Rotated: {steps}")
```

Positive values indicate clockwise rotation.

Negative values indicate counterclockwise rotation.

Example:

```text
+1
+2
-1
```

The reported direction can be reversed when creating an encoder.

## GPIO Rotary Encoder

The `GpioRotaryEncoder` reads a rotary encoder connected directly to Raspberry Pi GPIO pins.

The encoder uses two GPIO inputs for rotation:

- Channel A
- Channel B

An optional GPIO input can be used for the encoder push button.

### Pin Numbering

`GpioRotaryEncoderPins` uses physical Raspberry Pi header pin numbers.

For example:

```python
from hardware_io.rotary_encoder import (
    GpioRotaryEncoder,
    GpioRotaryEncoderPins,
)


encoder = GpioRotaryEncoder(
    pins=GpioRotaryEncoderPins(
        pin_a=11,
        pin_b=13,
        button=15,
    )
)
```

In this example:

```text
Physical Pin 11 -> BCM GPIO17
Physical Pin 13 -> BCM GPIO27
Physical Pin 15 -> BCM GPIO22
```

Physical header pin numbers are converted to BCM GPIO numbers using the GPIO header mapping.

### Using the GPIO Encoder

```python
import time

from hardware_io.rotary_encoder import (
    GpioRotaryEncoder,
    GpioRotaryEncoderPins,
)


def rotated(steps: int) -> None:
    print(f"Rotated: {steps}")


def button_pressed() -> None:
    print("Button pressed")


def button_released() -> None:
    print("Button released")


encoder = GpioRotaryEncoder(
    pins=GpioRotaryEncoderPins(
        pin_a=11,
        pin_b=13,
        button=15,
    )
)

encoder.start(
    rotated=rotated,
    button_pressed=button_pressed,
    button_released=button_released,
)

try:
    while True:
        encoder.poll()
        time.sleep(0.01)

except KeyboardInterrupt:
    pass

finally:
    encoder.cleanup()
```

The `poll()` method dispatches accumulated rotation events and should be called
periodically. `tick()` remains as a backward-compatible alias.

## Seesaw Rotary Encoder

The `SeesawRotaryEncoder` reads a rotary encoder through an Adafruit Seesaw I2C device.

Multiple Seesaw rotary encoders can share the same I2C bus.

Each Seesaw device must use a unique I2C address.

The default address is:

```text
0x36
```

Additional encoders can be configured using different addresses.

For example:

```text
Encoder 1 -> 0x36
Encoder 2 -> 0x37
Encoder 3 -> 0x38
```

The I2C address is configured using the address jumpers on the Seesaw board.

### Using One Seesaw Encoder

```python
from hardware_io.rotary_encoder import SeesawRotaryEncoder


def rotated(steps: int) -> None:
    print(f"Rotated: {steps}")


def button_pressed() -> None:
    print("Button pressed")


def button_released() -> None:
    print("Button released")


encoder = SeesawRotaryEncoder(
    address=0x36,
)

encoder.start(
    rotated=rotated,
    button_pressed=button_pressed,
    button_released=button_released,
)
```

The Seesaw encoder monitors rotation and button events in a background thread.

The Seesaw implementation inherits the no-op `poll()` behavior because it
monitors events in its own background thread.

### Using Multiple Seesaw Encoders

A single I2C bus can be shared between multiple encoders.

```python
import board

from hardware_io.rotary_encoder import SeesawRotaryEncoder


i2c = board.I2C()

encoder_1 = SeesawRotaryEncoder(
    address=0x36,
    i2c=i2c,
)

encoder_2 = SeesawRotaryEncoder(
    address=0x37,
    i2c=i2c,
)

encoder_3 = SeesawRotaryEncoder(
    address=0x38,
    i2c=i2c,
)
```

Each encoder can use its own callbacks.

## Required Libraries

### GPIO Rotary Encoder

The GPIO implementation requires the Raspberry Pi GPIO library.

On Raspberry Pi OS:

```bash
sudo apt install python3-rpi.gpio
```

The Python package can also be installed using:

```bash
python3 -m pip install RPi.GPIO
```

### Seesaw Rotary Encoder

The Seesaw implementation requires the Adafruit Blinka and Seesaw libraries.

Install the required Python packages using:

```bash
python3 -m pip install \
    adafruit-blinka \
    adafruit-circuitpython-seesaw
```

### I2C Support

I2C must be enabled on the Raspberry Pi when using Seesaw rotary encoders.

I2C can be enabled using:

```bash
sudo raspi-config
```

Select:

```text
Interface Options
    -> I2C
        -> Enable
```

The connected I2C devices can be displayed using `i2cdetect`.

Install the I2C tools:

```bash
sudo apt install i2c-tools
```

Scan the I2C bus:

```bash
i2cdetect -y 1
```

Example output with three Seesaw encoders:

```text
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- 36 37 38 -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
```

The addresses `0x36`, `0x37`, and `0x38` indicate three detected Seesaw devices.

## Component Tests

Example CLI applications are provided in the `component_test` directory.

```text
rotary_encoder/
├── __init__.py
├── rotary_encoder_if.py
├── gpio_rotary_encoder.py
├── seesaw_rotary_encoder.py
├── README.md
└── component_test/
    ├── __init__.py
    ├── gpio_rotary_encoder_cli.py
    └── seesaw_rotary_encoder_cli.py
```

## GPIO Encoder Component Test

Run the GPIO rotary encoder component test from the project root:

```bash
python3 -m hardware_io.rotary_encoder.component_test.gpio_rotary_encoder_cli \
    --pin-a 11 \
    --pin-b 13 \
    --button 15
```

The pin arguments use physical Raspberry Pi header pin numbers.

Example output:

```text
GPIO rotary encoder component test
Channel A physical pin: 11
Channel B physical pin: 13
Button physical pin: 15
Press Ctrl+C to stop.

Rotated clockwise: +1
Rotated clockwise: +1
Button pressed
Button released
Rotated counterclockwise: -1
```

Use the `--reverse` option to reverse the reported rotation direction:

```bash
python3 -m hardware_io.rotary_encoder.component_test.gpio_rotary_encoder_cli \
    --pin-a 11 \
    --pin-b 13 \
    --button 15 \
    --reverse
```

Press `Ctrl+C` to stop the component test.

## Seesaw Encoder Component Test

The Seesaw component test can monitor one or more rotary encoders on a shared
I2C bus. Pass the addresses of all connected encoders to `--addresses`. Each
address must be unique.

When `--addresses` is omitted, the test uses three encoders at:

```text
0x36
0x37
0x38
```

Run the component test from the project root:

```bash
python3 -m hardware_io.rotary_encoder.component_test.seesaw_rotary_encoder_cli
```

To test a single encoder:

```bash
python3 -m hardware_io.rotary_encoder.component_test.seesaw_rotary_encoder_cli \
    --addresses 0x36
```

To test two encoders:

```bash
python3 -m hardware_io.rotary_encoder.component_test.seesaw_rotary_encoder_cli \
    --addresses 0x36 0x37
```

Additional addresses can be supplied in the same way to test any number of
encoders:

```bash
python3 -m hardware_io.rotary_encoder.component_test.seesaw_rotary_encoder_cli \
    --addresses 0x36 0x37 0x38 0x39
```

Encoders are named `encoder-1` through `encoder-N` in the order their addresses
appear on the command line.

Example output:

```text
Initializing shared I2C bus...

Seesaw rotary encoder component test
Configured encoders:
  encoder-1: 0x36
  encoder-2: 0x37
  encoder-3: 0x38

Rotate or press any encoder.
Press Ctrl+C to stop.

[encoder-1 0x36] rotated clockwise: +1
[encoder-2 0x37] button pressed
[encoder-2 0x37] button released
[encoder-3 0x38] rotated counterclockwise: -1
```

Use the `--reverse` option to reverse the reported rotation direction for all encoders:

```bash
python3 -m hardware_io.rotary_encoder.component_test.seesaw_rotary_encoder_cli \
    --addresses 0x36 0x37 \
    --reverse
```

Each Seesaw position counter is zeroed when its encoder is initialized. Position
changes are then read from the device's incremental-delta register instead of
being calculated from its signed 32-bit absolute position. Invalid half-range
deltas are ignored, so a normal encoder step is not reported as a large
`-2147483648` change.

Press `Ctrl+C` to stop the component test.

## Car UI Event Routing

The Car UI uses encoder `0x36` as the system-volume encoder by default.
Clockwise and counterclockwise steps from that encoder are routed to global
volume up and volume down operations regardless of which panel is displayed.
Pressing that encoder toggles system mute.

All other configured encoders are contextual. They are exposed to panels as
zero-based slots in configured device order, with the volume encoder omitted.
A panel manager can register generic callbacks after calling `prepare_panel()`:

```python
def show(self) -> None:
    if not self.prepare_panel("Example"):
        return

    self.set_encoder_callbacks(
        rotated=self._encoder_rotated,
        button_pressed=self._encoder_button_pressed,
        button_released=self._encoder_button_released,
    )

def _encoder_rotated(self, slot: int, steps: int) -> None:
    if slot == 0:
        self.adjust_primary_control(steps)
    elif slot == 1:
        self.adjust_secondary_control(steps)

def _encoder_button_pressed(self, slot: int) -> None:
    if slot == 0:
        self.activate_primary_control()

def _encoder_button_released(self, slot: int) -> None:
    pass
```

Rotation callbacks receive the contextual slot and signed step count. Button
callbacks receive the contextual slot. For example, devices at indexes
`[0, 1, 2]` with index `0` assigned to volume expose device index `1` as
contextual slot `0` and device index `2` as contextual slot `1`. Opening
another panel or menu clears the previous panel's callbacks. The volume encoder
is reserved for system volume and is never forwarded to panel callbacks. Its
button press toggles mute; its button release is ignored.

The configured encoder list and volume role are set in
`apps/carUi/config/car_ui_runtime.toml`:

```toml
[input.rotary_encoders]
volume_index = 0

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x36

[[input.rotary_encoders.devices]]
driver = "seesaw"
address = 0x37

[[input.rotary_encoders.devices]]
driver = "gpio"
pin_a = 11
pin_b = 13
button = 15
```

The `driver` may be `seesaw` or `gpio`. Seesaw devices require a unique 7-bit
`address`; GPIO devices require unique physical header pins. `volume_index`
selects one entry in device order and is independent of the hardware driver.

The Car UI event router receives only `RotaryEncoderIf` instances and logical
indexes. Seesaw addresses and GPIO pins remain confined to configuration and
runtime hardware construction.

### System Volume Encoder Component Test

Run the configuration-driven volume test from the project root:

```bash
python3 -m apps.carUi.input.component_test.volume_encoder_cli
```

The test loads `apps/carUi/config/car_ui_runtime.toml`, constructs and starts
only the device selected by `volume_index` through `RotaryEncoderIf`, and
routes it to the real PipeWire system-volume controller. Contextual encoders
are intentionally not started, so a missing panel encoder cannot block this
test. Each detected step prints the resulting volume:

```text
Car UI volume encoder component test
Volume encoder device index: 0
Initial system volume: 10/20
Initial mute state: unmuted
Rotate the configured volume encoder or press it to toggle mute.
Press Ctrl+C to stop.

Volume up   -> level 11/20
Audio muted
Audio unmuted
Volume down -> level 10/20
```

The test changes the actual default audio sink volume. It requires `wpctl` and
the configured encoder hardware. Use `--config` for another runtime TOML,
`--volume-steps` to change the reported range, or `--step-percent` to change
the PipeWire adjustment made per encoder step. The default is 20 reported
levels because the default 5% PipeWire increment divides the full range into
20 steps. The Car UI's eight-bar volume indicator is a separate visual scale.
Positive adjustments are limited to 100% to prevent PipeWire amplification.
In the full application, `VolumeManager` maps audio levels `0..20`
proportionally onto indicator bars `0..8`.
When muted, all eight bars use the red muted color while preserving the
underlying level for unmute.

## Design

The rotary encoder interface reports rotation and button events using callbacks.

Hardware-specific behavior is contained within each rotary encoder implementation.

The GPIO implementation uses Raspberry Pi GPIO interrupts and dispatches
accumulated rotation through the interface's `poll()` method.

The Seesaw implementation reads encoder state over I2C and monitors the devices using background threads.
