"""Normalize assembled OSM building polygons into bounded SI presentation data."""

import math
import re

from ui.navigation.local_building_state import LocalBuilding


def height(tags):
    for key,source,scale in (('height','osm-height',1),('building:levels','levels-estimate',3)):
        try:
            value = float(str(tags.get(key,'')).strip().removesuffix(' m'))*scale
            if math.isfinite(value) and 1 <= value <= 1000:
                return value,source
        except ValueError:
            pass
    return 9.0,'placeholder'


def source_identity(feature):
    properties = feature.get('properties') or {}
    kind,identity = properties.get('@type'),properties.get('@id')
    if kind in ('way','relation') and identity is not None:
        return f'{kind}/{identity}'
    identity = str(feature.get('id') or '')
    short = re.fullmatch(r'([wr])([0-9]+)',identity)
    if short:
        return ('way/' if short[1]=='w' else 'relation/')+short[2]
    return identity


def normalize_components(feature, bounds):
    tags = feature.get('properties') or {}
    if tags.get('building') in (None,'no'):
        return ()
    geometry = feature.get('geometry') or {}
    coordinates = geometry.get('coordinates') or []
    if geometry.get('type') == 'Polygon':
        polygons = [coordinates]
    elif geometry.get('type') == 'MultiPolygon':
        polygons = coordinates
    else:
        return ()
    if not 1 <= len(polygons) <= 64:
        return ()
    west,south,east,north = bounds
    def ring(points):
        converted = []
        for point in points:
            lon,lat = float(point[0]),float(point[1])
            if not (west <= lon <= east and south <= lat <= north):
                raise ValueError('Building outside selected coverage')
            converted.append((math.radians(lon),math.radians(lat)))
        return tuple(converted)
    value,source = height(tags)
    identity = source_identity(feature)
    result = []
    try:
        for index,polygon in enumerate(polygons):
            if not polygon:
                return ()
            source_id = f'{identity}#{index}' if identity.startswith('relation/') else ''
            building = LocalBuilding(ring(polygon[0]),value,source,
                                     tuple(ring(hole) for hole in polygon[1:]),source_id)
            result.append(building.document())
    except (ValueError,TypeError,IndexError):
        # Do not flatten holes or silently publish a partial multipart feature.
        return ()
    return tuple(result)


def normalize(feature, bounds):
    """Retain the existing single-outline adapter; builders use all components."""
    components = normalize_components(feature,bounds)
    return components[0] if len(components)==1 else None


def ring_identity(ring):
    """Match identical member outlines independent of direction/start vertex."""
    points = tuple(tuple(point) for point in ring[:-1])
    def canonical(values):
        start = min(range(len(values)),key=values.__getitem__)
        return values[start:]+values[:start]
    return min(canonical(points),canonical(tuple(reversed(points))))


def outer_members(opl):
    """Read only outer-way membership from Osmium's relation OPL output."""
    result = {}
    for line in opl.splitlines():
        fields = line.split()
        if not fields or not re.fullmatch(r'r[0-9]+',fields[0]):
            continue
        members = next((field[1:] for field in fields if field.startswith('M')),'')
        ways = {f'way/{match[1]}' for member in members.split(',')
                if (match := re.fullmatch(r'w([0-9]+)@(outer)?',member))}
        result['relation/'+fields[0][1:]] = ways
    return result
