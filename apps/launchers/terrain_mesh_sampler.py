"""One source-height field for every Cesium mesh LOD, using existing local grids."""
from collections import OrderedDict
from dataclasses import dataclass
import math
import threading
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

    def contains(self, x, y):
        w,s,e,n = self.bounds
        return w <= x <= e and s <= y <= n


def buckets(rows):
    result = {}
    for row in rows:
        w,s,e,n = (math.degrees(value) for value in row.bounds)
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
                if row.contains(x,y)]
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
        def evaluate(index):
            if index>=len(rows):return self.reference
            source = rows[index]; grid = self.grid(source)
            w,s,e,n = source.bounds
            dx,dy=(e-w)/(grid.width-1),(n-s)/(grid.height-1)
            col,row=(x-w)/dx,(n-y)/dy
            left=max(0,min(grid.width-2,math.floor(col)))
            top=max(0,min(grid.height-2,math.floor(row)))
            fx,fy=col-left,row-top
            at=lambda r,c:grid.heights_m[r*grid.width+c]
            value=(at(top,left)*(1-fx)+at(top,left+1)*fx)*(1-fy)+(at(top+1,left)*(1-fx)+at(top+1,left+1)*fx)*fy
            band=min(2,(grid.width-1)*.1,(grid.height-1)*.1);weight=1
            for distance,a,b in ((col,w-dx*.01,y),(grid.width-1-col,e+dx*.01,y),
                                 (grid.height-1-row,x,s-dy*.01),(row,x,n+dy*.01)):
                if distance>=band:continue
                neighbors=self.sources(a,b)
                if not any(other.priority>=source.priority and other.area<=source.area*1.1 for other in neighbors):
                    weight=min(weight,max(0,distance/band))
            if weight>=1:return value
            lower=next((i for i in range(index+1,len(rows)) if rows[i].priority<source.priority or rows[i].area>source.area*1.1),len(rows))
            fraction=weight*weight*(3-2*weight)
            return evaluate(lower)*(1-fraction)+value*fraction
        return evaluate(0)

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
