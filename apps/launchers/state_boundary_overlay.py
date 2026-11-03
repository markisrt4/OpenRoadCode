"""Load bundled Census geometry into the renderer-independent boundary contract."""

import json
import math
from pathlib import Path

from ui.navigation.boundary_overlay_state import BoundaryOverlayState, BoundaryRegionState


_SOURCE = Path(__file__).resolve().parents[2] / 'resources/maps/us_state_boundaries.geojson'

_STATE_FIPS = frozenset({
    '01','02','04','05','06','08','09','10','12','13','15','16','17','18','19','20',
    '21','22','23','24','25','26','27','28','29','30','31','32','33','34','35','36',
    '37','38','39','40','41','42','44','45','46','47','48','49','50','51','53','54',
    '55','56',
})


def _rings(geometry):
    coordinates = geometry.get('coordinates')
    if geometry.get('type') == 'Polygon':
        return coordinates
    if geometry.get('type') == 'MultiPolygon':
        return [ring for polygon in coordinates for ring in polygon]
    raise ValueError('State boundary asset contains unsupported geometry')


def _segments(features):
    """Return unique undirected segments plus Michigan's emphasized outline."""
    unique = {}
    michigan = {}
    for feature in features:
        is_michigan = feature['properties']['GEOID'] == '26'
        for ring in _rings(feature.get('geometry', {})):
            points = [tuple(map(float, point[:2])) for point in ring]
            for start, end in zip(points, points[1:]):
                key = tuple(sorted((start, end)))
                unique.setdefault(key, (start, end))
                if is_michigan:
                    michigan.setdefault(key, (start, end))
    return unique.values(), michigan.values()


def _paths(segments):
    """Join an undirected segment set into maximal non-branching paths."""
    edges = {frozenset((start, end)) for start, end in segments if start != end}
    neighbors = {}
    for edge in edges:
        start, end = tuple(edge)
        neighbors.setdefault(start, set()).add(end)
        neighbors.setdefault(end, set()).add(start)
    paths = []

    def walk(start, end):
        path = [start, end]
        edges.remove(frozenset((start, end)))
        while len(neighbors[end]) == 2:
            following = next((point for point in neighbors[end]
                              if frozenset((end, point)) in edges), None)
            if following is None:
                break
            path.append(following)
            edges.remove(frozenset((end, following)))
            end = following
        return tuple((math.radians(lon), math.radians(lat)) for lon, lat in path)

    for start in sorted(point for point, adjacent in neighbors.items() if len(adjacent) != 2):
        for end in sorted(neighbors[start]):
            if frozenset((start, end)) in edges:
                paths.append(walk(start, end))
    while edges:
        start, end = tuple(next(iter(edges)))
        paths.append(walk(start, end))
    return tuple(paths)


def load_state_boundary_overlay(source=_SOURCE):
    document = json.loads(Path(source).read_text())
    features = document.get('features', ())
    fips = {feature.get('properties', {}).get('GEOID') for feature in features}
    if document.get('type') != 'FeatureCollection' or fips != _STATE_FIPS or len(features) != 50:
        raise ValueError('State boundary asset must contain exactly the 50 reviewed states')
    national, michigan = _segments(features)
    regions = (
        BoundaryRegionState('United States state boundaries', False, _paths(national)),
        BoundaryRegionState('Michigan', True, _paths(michigan)),
    )
    return BoundaryOverlayState(regions, 'U.S. Census Bureau · 2024 cartographic boundaries for statistical use')
