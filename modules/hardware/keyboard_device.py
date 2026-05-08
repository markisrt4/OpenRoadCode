import tkinter as tk
from typing import Callable

from .input_device_if import InputDeviceIf


class KeyboardDevice(InputDeviceIf):
    def __init__(self, root: tk.Widget):
        self.root = root
        self.bindings: dict[str, Callable[[], None]] = {}
        self.enabled = False

    def bind(self, input_name: str, callback: Callable[[], None]) -> None:
        self.bindings[input_name] = callback

        if self.enabled:
            self._bind_key(input_name, callback)

    def unbind(self, input_name: str) -> None:
        self.bindings.pop(input_name, None)
        self.root.unbind_all(input_name)

    def start(self) -> None:
        if self.enabled:
            return

        self.enabled = True

        for input_name, callback in self.bindings.items():
            self._bind_key(input_name, callback)

    def stop(self) -> None:
        if not self.enabled:
            return

        self.enabled = False

        for input_name in list(self.bindings.keys()):
            self.root.unbind_all(input_name)

    def _bind_key(self, input_name: str, callback: Callable[[], None]) -> None:
        self.root.bind_all(input_name, lambda event: callback())