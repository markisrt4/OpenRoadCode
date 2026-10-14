"""Read orientation layers from the installed MBTiles; no hosted map services."""
from collections import OrderedDict
from contextlib import closing
import math
import sqlite3
import threading
import zlib

from common.navigation_data import navigation_data_root
from tools.map_builder.builder.inspect_mvt import inspect_tile
from tools.map_builder.builder.validate import _decode_packed_varints, _decode_zigzag32
from ui.navigation import GeoPoint
from ui.navigation.road_overlay_state import RoadOverlayLine, PlaceOverlayLabel, RoadOverlayState

KINDS = {'motorway','trunk','primary','secondary','tertiary','minor','residential','unclassified','service'}


def geometry_paths(raw):
    values=_decode_packed_varints(raw)
    index=x=y=0
    paths=[]
    while index<len(values):
        header=values[index];index+=1
        command,count=header&7,header>>3
        if command not in (1,2) or count == 0 or index+count*2>len(values) or count>20000:
            raise ValueError('Invalid road geometry commands')
        for _ in range(count):
            x+=_decode_zigzag32(values[index]);y+=_decode_zigzag32(values[index+1]);index+=2
            if abs(x)>65536 or abs(y)>65536:
                raise ValueError('Road coordinate exceeds bounds')
            if command==1:
                paths.append([])
            if not paths:
                raise ValueError('Road line has no starting point')
            paths[-1].append((x,y))
    return paths


def decode_overlay(blob,z,x,y):
    if blob[:2]==b'\x1f\x8b':
        decoder=zlib.decompressobj(31)
        blob=decoder.decompress(blob,8*1024*1024+1)
        if not decoder.eof:
            raise ValueError('Road tile decompression exceeds limit')
    if len(blob)>8*1024*1024:
        raise ValueError('Road tile exceeds limit')
    roads=[];places=[];point_budget=12000
    features=inspect_tile(blob)
    def priority(feature):
        if feature['layer'] != 'place':
            return (0, 0, 0)
        attrs = feature['attributes']
        kind = attrs.get('class', '')
        kind_rank = {'city': 0, 'town': 1, 'village': 2, 'suburb': 3}.get(kind, 9)
        try:
            rank = int(attrs.get('rank', 99))
        except (TypeError, ValueError):
            rank = 99
        try:
            population = int(str(attrs.get('population', '0')).replace(',', ''))
        except (TypeError, ValueError):
            population = 0
        return (1, kind_rank, rank, -population)
    features.sort(key=priority)
    for feature in features:
        layer=feature['layer'];attrs=feature['attributes'];kind=attrs.get('class','')
        if layer not in ('transportation','transportation_name','place'):
            continue
        if layer=='place':
            allowed = ({'city'} if z <= 10 else {'city','town'} if z == 11
                       else {'city','town','village'} if z == 12
                       else {'city','town','village','suburb'})
            budget = 1 if z <= 11 else 2 if z <= 12 else 3
            if kind not in allowed or len(places) >= budget:
                continue
        if layer!='place' and (kind not in KINDS or feature['geometry_type']!=2
                               or (kind in {'minor','residential','unclassified','service'} and z<13)):
            continue
        extent=feature['extent']
        if not 256<=extent<=8192:
            raise ValueError('Unsupported road tile extent')
        def point(px,py):
            n=2**z
            return GeoPoint(math.atan(math.sinh(math.pi*(1-2*(y+py/extent)/n))),
                            (((x+px/extent)/n*2*math.pi)%(2*math.pi))-math.pi)
        name=str(attrs.get('name:en') or attrs.get('name:latin') or attrs.get('name') or '')[:80]
        for path in geometry_paths(feature['geometry']):
            if layer=='place' and path:
                px,py=path[0]
                if name and 0<=px<extent and 0<=py<extent:
                    places.append(PlaceOverlayLabel(name,point(px,py)))
            elif feature['geometry_type']==2 and 1<len(path)<=point_budget and len(roads)<500:
                point_budget-=len(path)
                label=str((attrs.get('ref') or name) if kind in {'motorway','trunk'} else (name or attrs.get('ref') or ''))[:80] if layer=='transportation_name' else ''
                roads.append(RoadOverlayLine(kind,tuple(point(px,py) for px,py in path),label))
    return RoadOverlayState(tuple(roads),tuple(places))


class LocalRoadOverlay:
    def __init__(self,path):
        self.path=path.resolve()
        self.max_zoom=14
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.5)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone():
                row=db.execute("SELECT value FROM metadata WHERE name='maxzoom'").fetchone()
                if row:
                    self.max_zoom=max(8,min(14,int(row[0])))
        self._cache=OrderedDict()
        self._lock=threading.Lock()

    @classmethod
    def installed(cls):
        path=navigation_data_root()/'maps/vector/openroadcode.mbtiles'
        if not path.is_file():
            return None
        try:
            return cls(path)
        except (OSError,sqlite3.Error,ValueError):
            return None

    def tile(self,z,x,y):
        if not 8<=z<=14 or not 0<=x<2**z or not 0<=y<2**z:
            raise ValueError('Invalid road tile coordinates')
        key=(z,x,y)
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        with closing(sqlite3.connect(self.path.as_uri()+'?mode=ro&immutable=1',uri=True,timeout=.5)) as db:
            row=db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',
                           (z,x,2**z-1-y)).fetchone()
            # City labels can disappear from detailed tiles. Read their overview
            # parent too, retaining only labels owned by this requested tile.
            overview = min(z, 10)
            scale = 2**(z-overview)
            parent = db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?',
                                (overview,x//scale,2**overview-1-y//scale)).fetchone() if overview<z else None
        state=decode_overlay(row[0],z,x,y) if row else RoadOverlayState()
        if parent:
            places=list(state.places)
            seen={(place.name,place.point) for place in places}
            for place in decode_overlay(parent[0],overview,x//scale,y//scale).places:
                point=place.point
                px=int((point.longitude_rad+math.pi)/(2*math.pi)*2**z)
                py=int((1-math.asinh(math.tan(point.latitude_rad))/math.pi)/2*2**z)
                if (px,py)==(x,y) and (place.name,point) not in seen and len(places)<60:
                    places.append(place);seen.add((place.name,point))
            state=RoadOverlayState(state.roads,tuple(places))
        with self._lock:
            self._cache[key]=state
            while len(self._cache)>32:
                self._cache.popitem(last=False)
        return state
