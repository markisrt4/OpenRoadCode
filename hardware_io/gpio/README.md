# GPIO

The `gpio` component provides Raspberry Pi GPIO header and pin information.

It provides mappings between physical Raspberry Pi header pin numbers and BCM GPIO numbers.

## GPIO Pin

The `GpioPin` class describes a single Raspberry Pi header pin.

Each pin contains:

- Physical header pin number
- BCM GPIO number, when applicable
- Pin name
- Default function

## Raspberry Pi GPIO Header

The `RpiGpioHeader` class provides the Raspberry Pi 40-pin GPIO header mapping.

Pins can be looked up using either a physical header pin number or BCM GPIO number.

## Example

```python
from hardware_io.gpio import RpiGpioHeader


pin = RpiGpioHeader.by_physical_pin(11)

print(pin.physical_pin)
print(pin.bcm)
print(pin.name)
print(pin.function)
```

Example output:

```text
11
17
GPIO17
GPIO
```

BCM and physical pin numbers can also be converted directly:

```python
bcm = RpiGpioHeader.bcm_from_physical_pin(11)

physical_pin = RpiGpioHeader.physical_pin_from_bcm(17)
```

## Component Test

A simple CLI application is provided in the `component_test` directory.

Run the test from the project root:

```bash
python3 -m hardware_io.gpio.component_test.gpio_header_cli
```

The component test displays the Raspberry Pi GPIO header pin mapping.

## Design

This component describes the Raspberry Pi GPIO header and pin mappings.

It does not configure, read, or write GPIO pins. Hardware-specific GPIO operations should be handled by separate GPIO components.
