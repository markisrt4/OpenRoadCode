"""One source-height field for every Cesium mesh LOD, using existing local grids."""
import math
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from apps.launchers.local_terrain_pack import _load_single_terrain
from ui.navigation.local_terrain_state import LocalTerrainState


@dataclass(frozen=True)
class TerrainSource:
    key: str
    bounds: tuple[float, float, float, float]
    width: int
    height: int
    priority: int
    load: Callable[[], LocalTerrainState]

    @property
    def area(self):
        w,s,e,n = self.bounds
        return (e-w)*(n-s)/((self.width-1)*(self.height-1))

    @property
    def support_bounds(self):
        w,s,e,n = self.bounds
        dx,dy = 2*(e-w)/(self.width-1),2*(n-s)/(self.height-1)
        return w-dx,s-dy,e+dx,n+dy

    def supports(self, x, y):
        w,s,e,n = self.support_bounds
        return w <= x <= e and s <= y <= n

    def contains(self, x, y):
        w,s,e,n = self.bounds
        return w <= x <= e and s <= y <= n


def buckets(rows):
    result = {}
    for row in rows:
        w,s,e,n = (math.degrees(value) for value in row.support_bounds)
        for x in range(math.floor(w),math.floor(e)+1):
            for y in range(math.floor(s),math.floor(n)+1):
                result.setdefault((x,y),[]).append(row)
    return result


class TerrainMeshSampler:
    def __init__(self, catalog):
        self.reference = catalog.state.tiles[0].reference_height_m if catalog.state.tiles else 0
        self.index = getattr(catalog, 'index', None)
        baseline = []
        for metadata, path in zip(catalog.state.tiles, catalog.payloads):
            coverage = metadata.coverage
            baseline.append(TerrainSource(metadata.tile_id,
                (coverage.west_rad,coverage.south_rad,coverage.east_rad,coverage.north_rad),
                metadata.width,metadata.height,metadata.detail_level,
                lambda path=path:_load_single_terrain(path.parent)))
        self.baseline = buckets(baseline)
        self.cache = OrderedDict(); self.meshes = OrderedDict(); self.lock = threading.RLock()

    def sources(self, x, y):
        rows = [row for row in self.baseline.get((math.floor(math.degrees(x)),math.floor(math.degrees(y))),())
                if row.supports(x,y)]
        if self.index is not None:
            rows.extend(self.index.point_sources(x,y))
        return sorted(rows,key=lambda row:(-row.priority,row.area,row.key))

    def grid(self, source):
        with self.lock:
            if source.key not in self.cache:
                self.cache[source.key] = source.load()
            self.cache.move_to_end(source.key)
            while len(self.cache)>32:
                self.cache.popitem(last=False)
            return self.cache[source.key]

    def value(self, x, y):
        rows = self.sources(x,y)
        # Blend across both sides of a source border, including adjacent packs
        # with different edge samples. Keeping each side unchanged at the exact
        # edge preserves a discontinuity even when mesh LODs agree there.
        def smooth(value):
            value=max(0,min(1,value))
            return value*value*(3-2*value)

        def contribution(source):
            w,s,e,n=source.bounds
            dx,dy=(e-w)/(source.width-1),(n-s)/(source.height-1)
            col,row=(x-w)/dx,(n-y)/dy
            band=min(2,(source.width-1)*.1,(source.height-1)*.1)
            weight=1
            for distance in (col,source.width-1-col,row,source.height-1-row):
                weight*=smooth((distance+band)/(2*band))
            if not weight:return 0,0
            grid=self.grid(source)
            col=max(0,min(grid.width-1,col));row=max(0,min(grid.height-1,row))
            left=min(grid.width-2,math.floor(col));top=min(grid.height-2,math.floor(row))
            fx,fy=col-left,row-top
            at=lambda r,c:grid.heights_m[r*grid.width+c]
            value=(at(top,left)*(1-fx)+at(top,left+1)*fx)*(1-fy)+(at(top+1,left)*(1-fx)+at(top+1,left+1)*fx)*fy
            return value,weight

        def evaluate(candidates):
            if not candidates:return self.reference
            first=candidates[0]
            peers=[source for source in candidates if source.priority==first.priority and source.area<=first.area*1.1]
            lower=[source for source in candidates if source not in peers]
            values=[contribution(source) for source in peers]
            total=sum(weight for _,weight in values)
            if not total:return evaluate(lower)
            value=sum(height*weight for height,weight in values)/total
            if total>=1:return value
            return value*total+evaluate(lower)*(1-total)
        return evaluate(rows)

    def mesh(self, zoom, x, y):
        if any(type(v) is not int for v in (zoom,x,y)) or not 0<=zoom<=16 or not 0<=x<2**(zoom+1) or not 0<=y<2**zoom:
            raise ValueError('Invalid terrain mesh address')
        key=(zoom,x,y)
        with self.lock:
            if key in self.meshes:
                self.meshes.move_to_end(key);return self.meshes[key]
        # Dyadic integer lattice: shared coordinates are identical at every LOD.
        heights=[]
        for row in range(33):
            latitude=math.radians(90-(y*32+row)*180/(32*2**zoom))
            for col in range(33):
                longitude=math.radians(-180+(x*32+col)*360/(32*2**(zoom+1)))
                heights.append(self.value(longitude,latitude))
        result=dict(width=33,height=33,heights_m=heights,reference_height_m=self.reference)
        with self.lock:
            self.meshes[key]=result
            while len(self.meshes)>8:self.meshes.popitem(last=False)
        return result
