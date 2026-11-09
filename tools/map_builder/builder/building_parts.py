"""Associate contained OSM parts with outlines without per-building service calls."""
import math

from ui.navigation.local_building_state import _inside_ring

CELL = math.radians(.01)


def bounds(building):
    points = building['ring_rad']
    return (min(p[0] for p in points),min(p[1] for p in points),
            max(p[0] for p in points),max(p[1] for p in points))


def cells(extent):
    w,s,e,n = (math.floor(value/CELL) for value in extent)
    for x in range(w,e+1):
        for y in range(s,n+1):
            yield x,y


def inside_or_boundary(point, ring):
    if _inside_ring(point,ring):
        return True
    x,y = point
    for (ax,ay),(bx,by) in zip(ring,ring[1:]):
        cross = (x-ax)*(by-ay)-(y-ay)*(bx-ax)
        if abs(cross)<1e-16 and min(ax,bx)-1e-12 <= x <= max(ax,bx)+1e-12 and min(ay,by)-1e-12 <= y <= max(ay,by)+1e-12:
            return True
    return False


def mark_part_outlines(buckets):
    """OSM outlines describe extents; contained parts supply the 3D shape.

    Match only complete accepted parts. Spatial indexing avoids comparing every
    suburban footprint with every part. Large extents use a bounded fallback.
    """
    indexed = {}
    for bucket in buckets.values():
        for building in bucket.values():
            if not building.get('is_part'):
                continue
            extent = bounds(building)
            # Index parts by their first point; containment requires that point
            # within the parent, even when the part crosses a tile boundary.
            x,y = building['ring_rad'][0]
            indexed.setdefault((math.floor(x/CELL),math.floor(y/CELL)),[]).append((extent,building))
    count = 0
    for bucket in buckets.values():
        for building in bucket.values():
            if building.get('is_part'):
                continue
            extent = bounds(building)
            w,s,e,n = extent
            if (e-w)*(n-s)/CELL**2 > 10000:
                candidates = (part for group in indexed.values() for part in group)
            else:
                candidates = (part for key in cells(extent) for part in indexed.get(key,()))
            for (pw,ps,pe,pn),part in candidates:
                if not (w-1e-12 <= pw <= pe <= e+1e-12 and s-1e-12 <= ps <= pn <= n+1e-12):
                    continue
                points = part['ring_rad'][:-1]
                if (all(inside_or_boundary(point,building['ring_rad']) for point in points)
                        and not any(_inside_ring(point,hole) for hole in building.get('holes_rad',()) for point in points)):
                    building['outline_only'] = True
                    count += 1
                    break
    return count
