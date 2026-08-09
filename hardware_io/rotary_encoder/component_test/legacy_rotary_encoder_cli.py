from time import sleep

from modules.hardware.gpio.rpi_gpio import RpiGpio
from modules.hardware.drivers.rotary_encoder import RotaryEncoder, RotaryEncoderPins


def on_rotate(delta: int) -> None:
    print(f"Encoder rotated: {delta}")


def on_button() -> None:
    print("Button pressed!")


pins = RotaryEncoderPins(
    pin_a=RpiGpio.bcm_from_pin(36),   # GPIO16
    pin_b=RpiGpio.bcm_from_pin(38),   # GPIO20
    button=RpiGpio.bcm_from_pin(32),  # GPIO12
)

try:
    with RotaryEncoder(
        pins=pins,
        rotate_callback=on_rotate,
        button_callback=on_button,
    ) as encoder:
        while True:
            encoder.tick()
            sleep(0.01)

except KeyboardInterrupt:
    print("Exiting.")
