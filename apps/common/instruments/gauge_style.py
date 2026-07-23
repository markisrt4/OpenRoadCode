from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GaugeStyle:
    """Define the color palette used to render an instrument gauge."""
    background: str = "#08111a"
    face: str = "#101820"
    arc: str = "#24445c"
    tick: str = "#7fa8c8"
    title: str = "#9fd7ff"
    value: str = "#ffffff"
    unit: str = "#7fa8c8"
    needle: str = "#ff9f1c"
