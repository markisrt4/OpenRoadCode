from modules.hardware.keyboard_device import KeyboardDevice
from modules.sdr.radio_controller import RadioController
from .radio_input_adapter_if import RadioInputAdapterIf


class KeyboardRadioAdapter(RadioInputAdapterIf):
    def __init__(
        self,
        keyboard: KeyboardDevice,
        radio: RadioController,
    ):
        self.keyboard = keyboard
        self.radio = radio

    def connect(self) -> None:
        self.keyboard.bind("<Right>", self.radio.frequency_up)
        self.keyboard.bind("<Up>", self.radio.frequency_up)

        self.keyboard.bind("<Left>", self.radio.frequency_down)
        self.keyboard.bind("<Down>", self.radio.frequency_down)

        self.keyboard.bind("<n>", self.radio.next_station)
        self.keyboard.bind("<Next>", self.radio.next_station)

        self.keyboard.bind("<p>", self.radio.previous_station)
        self.keyboard.bind("<Prior>", self.radio.previous_station)

        self.keyboard.bind("<space>", self.radio.start)

        self.keyboard.start()

    def disconnect(self) -> None:
        self.keyboard.stop()
