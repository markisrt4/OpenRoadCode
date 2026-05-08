from dataclasses import dataclass

@dataclass(frozen=True)
class RadioRange:
    min_frequency_hz: int
    max_frequency_hz: int
    start_frequency_hz: int

@dataclass(frozen=True)
class RadioMode:
    name: str
    bandwidth: int
    step_hz: int


@dataclass(frozen=True)
class RadioPreset:
    label: str
    frequency_hz: int
    mode: RadioMode

    @property
    def frequency_mhz(self) -> float:
        return self.frequency_hz / 1_000_000
