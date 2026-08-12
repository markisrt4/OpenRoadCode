# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from time import sleep

from modules.hardware.gpio.rpi_gpio import RpiGpio
from modules.hardware.drivers.rotary_encoder import RotaryEncoderPins
from modules.hardware.input.rotary_encoder_device import RotaryEncoderDevice
from modules.sdr.rigctl_client import RigctlClient
from modules.adapters.rotary_rigctl_adapter import (
    RotaryRigctlAdapter,
    RotaryRigctlAdapterConfig,
)


def main() -> None:
    encoder = RotaryEncoderDevice(
        pins=RotaryEncoderPins(
            pin_a=RpiGpio.bcm_from_pin(36),
            pin_b=RpiGpio.bcm_from_pin(38),
            button=RpiGpio.bcm_from_pin(32),
        )
    )

    rigctl = RigctlClient(
        host="192.168.1.100",  # Radio Pi running SDR++ rigctl server
        port=4532,
    )

    adapter = RotaryRigctlAdapter(
        encoder=encoder,
        rigctl=rigctl,
        config=RotaryRigctlAdapterConfig(
            step_hz=25_000,
        ),
    )

    adapter.bind()
    encoder.start()

    try:
        while True:
            encoder.tick()
            sleep(0.01)

    except KeyboardInterrupt:
        pass

    finally:
        encoder.cleanup()


if __name__ == "__main__":
    main()
