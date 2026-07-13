import socket

SDRPP_MODE_MAP = {
    "NFM": "FM",
    "FM": "FM",
    "WFM": "WFM",
    "AM": "AM",
}

class RigctlClient:
    def __init__(self, host="127.0.0.1", port=4532, timeout=1.0):
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: str) -> str:
        command = command.rstrip() + "\n"

        with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
            sock.sendall(command.encode("utf-8"))

            try:
                sock.settimeout(self.timeout)
                return sock.recv(4096).decode("utf-8", errors="replace").strip()
            except socket.timeout:
                return ""

    def set_frequency(self, hz: int) -> str:
        return self.send(f"F {hz}")

    def get_frequency(self) -> str:
        return self.send("f")

    def set_mode(self, mode: str, bandwidth: int) -> str:
        rigctl_mode = self.normalize_sdrpp_mode(mode)
        return self.send(f"M {rigctl_mode} {bandwidth}")

    def start(self) -> str:
        return self.send(r"\start")

    def stop(self) -> str:
        return self.send(r"\stop")

    def get_signal_strength(self) -> str:
        return self.send("l STRENGTH")

    def get_snr(self) -> str:
        return self.send("l SNR")

    def get_rds(self) -> str:
        return self.send("l RDS")

    @staticmethod
    def normalize_sdrpp_mode(mode: str) -> str:
        return SDRPP_MODE_MAP.get(mode.upper(), mode.upper())
