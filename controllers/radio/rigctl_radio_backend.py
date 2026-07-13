from modules.radio.radio_backend_if import RadioBackendIf
from .rigctl_client import RigctlClient


class RigctlBackend(RadioBackendIf):
    def __init__(self, client: RigctlClient):
        self.client = client

    def start(self) -> str:
        return self.client.start()

    def stop(self) -> str:
        return self.client.stop()

    def set_frequency(self, frequency_hz: int) -> str:
        return self.client.set_frequency(frequency_hz)

    def get_frequency(self) -> int:
        return int(self.client.get_frequency())

    def set_mode(self, mode: str, bandwidth: int) -> str:
        return self.client.set_mode(mode, bandwidth)
