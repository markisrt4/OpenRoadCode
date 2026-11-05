"""Immutable, renderer-neutral presentation of optional map controls."""
from dataclasses import dataclass
from enum import Enum


class MapLayerAction(str, Enum):
    IMAGERY = 'imagery'
    BUILDINGS = 'buildings'
    ROADS = 'roads'
    PLACES = 'places'
    RELIEF = 'terrain'
    HEIGHT = 'terrain-scale'
    CUES = 'terrain-cues'
    GRID = 'references'


@dataclass(frozen=True, slots=True)
class MapLayerControl:
    action: MapLayerAction
    label: str
    available: bool
    enabled: bool

    def __post_init__(self) -> None:
        if (not isinstance(self.action,MapLayerAction) or not self.label.strip() or len(self.label)>40
                or type(self.available) is not bool or type(self.enabled) is not bool):
            raise ValueError('Invalid map layer control')


@dataclass(frozen=True, slots=True)
class MapLayerControls:
    controls: tuple[MapLayerControl, ...] = ()

    def __post_init__(self) -> None:
        if (not isinstance(self.controls,tuple) or len(self.controls)>len(MapLayerAction)
                or any(not isinstance(item,MapLayerControl) for item in self.controls)
                or len({item.action for item in self.controls})!=len(self.controls)):
            raise ValueError('Invalid immutable map layer controls')
