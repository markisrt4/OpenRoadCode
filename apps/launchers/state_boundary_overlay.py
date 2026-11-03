"""Load bundled Census geometry into the renderer-independent boundary contract."""

import json
import math
from pathlib import Path

from ui.navigation.boundary_overlay_state import BoundaryOverlayState, BoundaryRegionState


_SOURCE = Path(__file__).resolve().parents[2] / 'resources/maps/great_lakes_state_boundaries.geojson'


def load_state_boundary_overlay(source=_SOURCE):
    document = json.loads(Path(source).read_text())
    if document.get('type') != 'FeatureCollection' or len(document.get('features', ())) != 4:
        raise ValueError('State boundary asset must contain the four reviewed regions')
    regions = []
    for feature in document['features']:
        properties = feature.get('properties', {})
        name = properties.get('NAME')
        geometry = feature.get('geometry', {})
        coordinates = geometry.get('coordinates')
        if geometry.get('type') == 'Polygon':
            polygons = [coordinates]
        elif geometry.get('type') == 'MultiPolygon':
            polygons = coordinates
        else:
            raise ValueError('State boundary asset contains unsupported geometry')
        rings = tuple(
            tuple((math.radians(float(lon)), math.radians(float(lat))) for lon, lat in ring)
            for polygon in polygons for ring in polygon
        )
        regions.append(BoundaryRegionState(name, name == 'Michigan', rings))
    regions.sort(key=lambda region: (not region.emphasized, region.name))
    return BoundaryOverlayState(tuple(regions), 'U.S. Census Bureau TIGERweb · boundaries for statistical use')
