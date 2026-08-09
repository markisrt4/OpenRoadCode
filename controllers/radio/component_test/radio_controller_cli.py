"""Standalone component test for the radio controller package.

Run from the repository root:

    python3 -m controllers.radio.component_test
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from controllers.radio import RadioController, RadioMode, RadioPreset, RadioRange
from controllers.radio.adapters.rigctl_radio_backend import RigctlRadioBackend


@dataclass
class RecordingBackend:
    frequency_hz: int = 0
    mode: str = ""
    bandwidth: int = 0
    running: bool = False
    signal_strength: Optional[str] = "-42.5"
    snr: Optional[str] = "31.2"
    rds: Optional[str] = "TEST FM"
    calls: list[tuple[object, ...]] = field(default_factory=list)

    def start(self) -> str:
        self.running = True
        self.calls.append(("start",))
        return "RPRT 0"

    def stop(self) -> str:
        self.running = False
        self.calls.append(("stop",))
        return "RPRT 0"

    def set_frequency(self, frequency_hz: int) -> str:
        self.frequency_hz = frequency_hz
        self.calls.append(("set_frequency", frequency_hz))
        return "RPRT 0"

    def get_frequency(self) -> int:
        self.calls.append(("get_frequency",))
        return self.frequency_hz

    def set_mode(self, mode: str, bandwidth: int) -> str:
        self.mode = mode
        self.bandwidth = bandwidth
        self.calls.append(("set_mode", mode, bandwidth))
        return "RPRT 0"

    def get_signal_strength(self) -> Optional[str]:
        return self.signal_strength

    def get_snr(self) -> Optional[str]:
        return self.snr

    def get_rds(self) -> Optional[str]:
        return self.rds


class FakeRigctlClient:
    def __init__(self) -> None:
        self.frequency_response = "101100000"
        self.signal_strength_response: Optional[str] = " -42.5 "
        self.snr_response: Optional[str] = "31.2"
        self.rds_response: Optional[str] = " TEST FM "

    def start(self) -> str:
        return "RPRT 0"

    def stop(self) -> str:
        return "RPRT 0"

    def set_frequency(self, frequency_hz: int) -> str:
        self.frequency_response = str(frequency_hz)
        return "RPRT 0"

    def get_frequency(self) -> str:
        return self.frequency_response

    def set_mode(self, mode: str, bandwidth: int) -> str:
        return "RPRT 0"

    def get_signal_strength(self) -> Optional[str]:
        return self.signal_strength_response

    def get_snr(self) -> Optional[str]:
        return self.snr_response

    def get_rds(self) -> Optional[str]:
        return self.rds_response


def report_pass(name: str, detail: str | None = None) -> None:
    print(f"[PASS] {name}")
    if detail is not None:
        print(f"       {detail}")


def expect_value_error(action: object, description: str) -> None:
    try:
        action()  # type: ignore[operator]
    except ValueError:
        report_pass(description)
        return
    raise AssertionError(f"{description}: expected ValueError")


def main() -> None:
    print("Radio controller component test\n")

    wide_fm = RadioMode("wfm", bandwidth=180_000, step_hz=100_000)
    narrow_fm = RadioMode("nfm", bandwidth=12_500, step_hz=25_000)
    presets = [
        RadioPreset("88.7 FM", 88_700_000, wide_fm),
        RadioPreset("101.1 FM", 101_100_000, wide_fm),
        RadioPreset("NOAA", 162_550_000, narrow_fm),
    ]
    radio_range = RadioRange(87_500_000, 108_000_000, 88_100_000)
    backend = RecordingBackend()
    controller = RadioController(backend, presets, wide_fm, radio_range)

    assert controller.start() == 88_100_000
    assert backend.running
    assert backend.mode == "WFM"
    assert backend.bandwidth == 180_000
    report_pass(
        "Start controller and apply default configuration",
        "Frequency: 88100000 Hz, mode: WFM, bandwidth: 180000 Hz",
    )

    assert controller.frequency_up() == 88_200_000
    report_pass("Step frequency upward", "88100000 Hz -> 88200000 Hz")

    assert controller.frequency_down(200_000) == 88_000_000
    report_pass("Step frequency downward with explicit delta", "88200000 Hz -> 88000000 Hz")

    controller.set_frequency(108_000_000)
    assert controller.frequency_up() == 87_500_000
    assert controller.frequency_down() == 108_000_000
    report_pass("Wrap frequency at configured range boundaries")

    assert controller.next_preset() == presets[1]
    assert controller.next_station() == presets[2]
    assert controller.next_preset() == presets[0]
    assert controller.previous_station() == presets[2]
    assert controller.current_mode == narrow_fm
    report_pass("Navigate presets and compatibility aliases", "Current preset: NOAA")

    backend.frequency_hz = 99_900_000
    assert controller.refresh_frequency() == 99_900_000
    assert controller.get_frequency() == 99_900_000
    report_pass("Synchronize controller frequency from backend", "Frequency: 99900000 Hz")

    controller.stop()
    assert not backend.running
    report_pass("Stop controller")

    fake_client = FakeRigctlClient()
    rigctl_backend = RigctlRadioBackend(fake_client)
    assert rigctl_backend.get_frequency() == 101_100_000
    rigctl_backend.set_frequency(162_550_000)
    assert rigctl_backend.get_frequency() == 162_550_000
    report_pass("Adapt rigctl frequency operations", "Frequency: 162550000 Hz")

    assert rigctl_backend.get_signal_strength() == "-42.5"
    assert rigctl_backend.get_snr() == "31.2"
    assert rigctl_backend.get_rds() == "TEST FM"
    report_pass("Normalize optional rigctl status values", "Signal: -42.5, SNR: 31.2, RDS: TEST FM")

    fake_client.rds_response = "   "
    assert rigctl_backend.get_rds() is None
    fake_client.snr_response = None
    assert rigctl_backend.get_snr() is None
    report_pass("Convert empty optional rigctl values to None")

    invalid_client = FakeRigctlClient()
    invalid_client.frequency_response = "RPRT -1"
    try:
        RigctlRadioBackend(invalid_client).get_frequency()
    except RuntimeError:
        report_pass("Reject invalid rigctl frequency responses")
    else:
        raise AssertionError("invalid rigctl frequency response was not rejected")

    expect_value_error(
        lambda: RadioRange(108_000_000, 87_500_000, 100_000_000),
        "Reject invalid radio ranges",
    )
    expect_value_error(
        lambda: RadioMode("", bandwidth=12_500, step_hz=25_000),
        "Reject invalid radio modes",
    )
    expect_value_error(
        lambda: RadioPreset("", 101_100_000, wide_fm),
        "Reject invalid radio presets",
    )

    print("\nRadio controller component test: PASS")


if __name__ == "__main__":
    main()
