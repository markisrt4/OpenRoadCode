"""Bounded national terrain pages; no national sample arrays at startup."""
import hashlib
import json
import math
import re
import threading
from collections import OrderedDict
from pathlib import Path

from apps.launchers.local_terrain_pack import _load_single_terrain
from common.xdg_paths import openroadcode_data_dir
from ui.navigation.local_imagery_state import LocalImageryState
from ui.navigation.local_terrain_state import LocalTerrainTileIndexState


class NationalTerrainIndex:
    def __init__(self, root, document):
        self.root = Path(root).resolve()
        rows = document.get('tiles', [])
        if document.get('kind') != 'us-terrain-index' or not 1 <= len(rows) <= 4096:
            raise ValueError('Invalid national terrain catalog')
        self.rows = {}; self.cache = OrderedDict(); self.lock = threading.RLock()
        for row in rows:
            key = row['id']
            if (not re.fullmatch(r'(?:us-[a-z]{2}-overview(?:-[12])?|michigan-overview)--\d{1,2}', key)
                    or key in self.rows or not re.fullmatch('[a-f0-9]{64}', row['sha256'])):
                raise ValueError('Invalid national chunk identity')
            directory = (self.root/row['path']).resolve()
            if not directory.is_relative_to(self.root):
                raise ValueError('National chunk escapes managed storage')
            self.rows[key] = row

    def chunk(self, key):
        if key not in self.rows:
            raise ValueError('Unknown national terrain chunk')
        row = self.rows[key]
        directory = (self.root/row['path']).resolve()
        if not directory.is_relative_to(self.root):
            raise ValueError('National chunk escapes managed storage')
        payload = directory/'terrain.json'
        stat = payload.stat(); stamp = (stat.st_size, stat.st_mtime_ns)
        with self.lock:
            cached = self.cache.get(key)
            if cached is None or cached[0] != stamp:
                if stat.st_size > 2*1024*1024:
                    raise ValueError('Oversized national terrain chunk')
                content = payload.read_bytes()
                if hashlib.sha256(content).hexdigest() != row['sha256']:
                    raise ValueError('National terrain checksum mismatch')
                state = _load_single_terrain(directory)
                if state.width != row['width'] or state.height != row['height']:
                    raise ValueError('National terrain dimensions mismatch')
                cached = (stamp, content, state); self.cache[key] = cached
            self.cache.move_to_end(key)
            while len(self.cache) > 8:
                self.cache.popitem(last=False)
            return cached[1]

    def state(self,key):
        with self.lock:
            self.chunk(key)
            return self.cache[key][2]

    def point_sources(self,longitude,latitude):
        from apps.launchers.terrain_mesh_sampler import TerrainSource, buckets
        with self.lock:
            if not hasattr(self,'_point_buckets'):
                self._point_buckets=buckets([TerrainSource('national-'+key,
                    tuple(math.radians(value) for value in row['bounds_deg']),row['width'],row['height'],0,
                    lambda key=key:self.state(key)) for key,row in self.rows.items()])
            candidates=self._point_buckets.get((math.floor(math.degrees(longitude)),math.floor(math.degrees(latitude))),())
        return [source for source in candidates if source.supports(longitude,latitude)]

    def page(self, zoom, x, y, reference):
        if any(type(v) is not int for v in (zoom,x,y)) or not 0 <= zoom <= 16 or not 0 <= x < 2**(zoom+1) or not 0 <= y < 2**zoom:
            raise ValueError('Invalid national terrain page')
        if zoom < 8:
            return {'tiles': []}
        west=x/2**(zoom+1)*360-180; east=(x+1)/2**(zoom+1)*360-180
        north=90-y/2**zoom*180; south=90-(y+1)/2**zoom*180
        px=(east-west)/32;py=(north-south)/32
        west=max(-180,west-px);east=min(180,east+px);south=max(-90,south-py);north=min(90,north+py)
        selected = []
        for key, row in self.rows.items():
            a,b,c,d = row['bounds_deg']
            if a >= east or c <= west or b >= north or d <= south:
                continue
            coverage = LocalImageryState('US coarse terrain', 'USGS 3DEP · The National Map',
                                         *(math.radians(value) for value in (a,b,c,d)))
            state = LocalTerrainTileIndexState('us-'+key, coverage, row['width'], row['height'],
                                               reference, row['datum'], 0, 8)
            selected.append(state.document() | dict(url='/data/terrain-chunk/us-'+key))
        # Dense overlapping state envelopes may exceed the transport budget.
        # Closer zooms narrow the page and expose the remaining grids.
        selected.sort(key=lambda row: abs((row['west_rad']+row['east_rad'])/2-math.radians((west+east)/2)))
        return {'tiles': selected[:64], 'truncated': len(selected)>64}


class CombinedTerrainIndex:
    def __init__(self, detail, national):
        self.detail, self.national = detail, national

    def chunk(self, key):
        if key.startswith('us-'):
            return self.national.chunk(key[3:])
        if self.detail is None:
            raise ValueError('Unknown terrain chunk')
        return self.detail.chunk(key)

    def point_sources(self,longitude,latitude):
        detail=self.detail.point_sources(longitude,latitude) if self.detail else []
        return detail+self.national.point_sources(longitude,latitude)

    def page(self, zoom, x, y, reference):
        detail = self.detail.page(zoom,x,y,reference)['tiles'] if self.detail else []
        national = self.national.page(zoom,x,y,reference)
        return {'tiles': detail+national['tiles'][:64-len(detail)], 'truncated': national.get('truncated',False)}


def installed_national_index():
    root = openroadcode_data_dir('map-packs','us-terrain')
    path = root/'active/catalog.json'
    return NationalTerrainIndex(root, json.loads(path.read_text())) if path.is_file() else None
