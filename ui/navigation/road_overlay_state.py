"""Immutable SI road and place geometry for an offline orientation overlay."""
from dataclasses import dataclass
import math
from ui.navigation import GeoPoint


def _valid_point(point):
    return (isinstance(point,GeoPoint) and math.isfinite(point.latitude_rad) and math.isfinite(point.longitude_rad)
            and abs(point.latitude_rad)<=math.pi/2 and abs(point.longitude_rad)<=math.pi)


@dataclass(frozen=True, slots=True)
class RoadOverlayLine:
    kind: str
    points: tuple[GeoPoint, ...]
    label: str = ''
    geometry_visible: bool = True

    def __post_init__(self):
        if (self.kind not in {'motorway','trunk','primary','secondary','tertiary','minor','residential','unclassified','service'}
                or not isinstance(self.points,tuple) or not 2<=len(self.points)<=12000
                or len(self.label)>80 or type(self.geometry_visible) is not bool
                or not all(_valid_point(point) for point in self.points)):
            raise ValueError('Invalid SI road segment')

    def document(self):
        return {'kind':self.kind,
                'points':[[point.longitude_rad,point.latitude_rad] for point in self.points],
                'label':self.label, 'geometry_visible':self.geometry_visible}


@dataclass(frozen=True, slots=True)
class PlaceOverlayLabel:
    name: str
    point: GeoPoint

    def __post_init__(self):
        if not self.name.strip() or len(self.name)>80 or not _valid_point(self.point):
            raise ValueError('Invalid SI place label')

    def document(self):
        return {'name':self.name,'position':[self.point.longitude_rad,self.point.latitude_rad]}


@dataclass(frozen=True, slots=True)
class RoadOverlayState:
    roads: tuple[RoadOverlayLine, ...] = ()
    places: tuple[PlaceOverlayLabel, ...] = ()

    def __post_init__(self):
        if not isinstance(self.roads,tuple) or not isinstance(self.places,tuple) or len(self.roads)>500 or len(self.places)>60 or sum(len(road.points) for road in self.roads)>12000:
            raise ValueError('Road overlay exceeds immutable tile limits')

    def document(self):
        return {'roads':[road.document() for road in self.roads], 'places':[place.document() for place in self.places],
                'attribution':'© OpenStreetMap contributors · ODbL 1.0'}
