"""Optional offline building packs from existing OSM sources; no service queries."""
from datetime import datetime, timezone
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from ui.navigation.local_map_tiles_state import MAX_MAP_TILES
from ui.navigation.local_building_state import LocalBuilding
from .building_parts import mark_part_outlines
from .building_geometry import height, normalize, normalize_components, source_identity, ring_identity, outer_members

PRESETS = {
    'detroit-downtown': ('Detroit Downtown',(-83.065,42.315,-83.025,42.345)),
    'detroit-midtown': ('Detroit Downtown–Midtown',(-83.085,42.315,-83.025,42.375)),
    'pine-knob': ('Pine Knob · Clarkston',(-83.39,42.74,-83.365,42.765)),
    'rochester': ('Rochester test area',(-83.175,42.650,-83.110,42.705)),
    'southfield': ('Central Southfield test area',(-83.290,42.440,-83.220,42.505)),
    'metro-detroit': ('Metro Detroit',(-83.75,42.0,-82.55,42.9)),
}
CREDIT = '© OpenStreetMap contributors · ODbL 1.0'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def partition_buildings(buckets, bounds, rows, columns, *, adaptive=False):
    """Split dense Metro cells without truncating outlines or raising GPU limits."""
    west,south,east,north = bounds
    pending = deque((f'r{row}-c{col}',
        (west+(east-west)*col/columns,south+(north-south)*row/rows,
         west+(east-west)*(col+1)/columns,south+(north-south)*(row+1)/rows),
        list(features.values()),0) for (row,col),features in buckets.items())
    emitted = 0
    while pending:
        tile_id,extent,features,depth = pending.popleft()
        content = json.dumps({'attribution':CREDIT,'buildings':features},separators=(',',':')).encode()
        if len(content) <= 10*1024*1024 and len(features) <= 10000:
            emitted += 1
            yield tile_id,extent,features,content
            continue
        if not adaptive or depth >= 6 or emitted+len(pending)+4 > MAX_MAP_TILES:
            raise ValueError('Building tile exceeds runtime limits and bounded subdivision capacity')
        w,s,e,n = extent
        mid_x,mid_y = (w+e)/2,(s+n)/2
        groups = [[] for _ in range(4)]
        for building in features:
            ring = building['ring_rad'][:-1]
            lon = math.degrees(sum(point[0] for point in ring)/len(ring))
            lat = math.degrees(sum(point[1] for point in ring)/len(ring))
            groups[int(lat >= mid_y)*2+int(lon >= mid_x)].append(building)
        for index,group in enumerate(groups):
            row,col = divmod(index,2)
            child = (mid_x if col else w,mid_y if row else s,
                     e if col else mid_x,n if row else mid_y)
            pending.append((tile_id+'-'+str(index),child,group,depth+1))


def build_pack(root, preset):
    root = Path(root)
    title,bounds = PRESETS[preset]
    sources = sorted((root/'maps/source').glob('*.osm.pbf'))
    if not sources:
        raise ValueError('Build navigation data first: no source PBFs installed')
    destination = root/'maps/3d/packs'/preset
    if destination.exists():
        raise ValueError(f'Pack already exists: {destination}; validate or explicitly remove it before rebuilding')
    destination.parent.mkdir(parents=True,exist_ok=True)
    west,south,east,north = bounds
    rows,columns = (16,16) if preset == "metro-detroit" else (4,2)
    buckets = {(row,col):{} for row in range(rows) for col in range(columns)}
    height_counts = {key:0 for key in ("osm-height","levels-estimate","placeholder")}
    skipped = 0
    members, accepted_relations = {}, {}
    duplicates = 0
    with TemporaryDirectory(dir=destination.parent,prefix='.build-3d-') as temporary:
        scratch = Path(temporary)
        for index,source in enumerate(sources):
            extract,filtered = scratch/f'{index}.osm.pbf',scratch/f'{index}-buildings.osm.pbf'
            subprocess.run(['osmium','extract','-b',','.join(map(str,bounds)),'-s','smart','-S','types=multipolygon',
                            str(source),'-o',str(extract)],check=True)
            subprocess.run(['osmium','tags-filter',str(extract),'wr/building','wr/building:part','-o',str(filtered)],check=True)
            membership = subprocess.run(['osmium','cat','--object-type=relation','-f','opl',str(filtered)],
                                        check=True,capture_output=True,text=True)
            members.update(outer_members(membership.stdout))
            command = ['osmium','export',str(filtered),'--geometry-types=polygon',
                       '--add-unique-id=type_id','--attributes=type,id','-f','geojsonseq','-o','-']
            process = subprocess.Popen(command,stdout=subprocess.PIPE,text=True)
            try:
                for line in process.stdout:
                    if not line.strip():
                        continue
                    feature = json.loads(line.lstrip('\x1e'))
                    buildings = normalize_components(feature,bounds)
                    if not buildings:
                        skipped += 1
                        continue
                    identity = source_identity(feature)
                    if not identity:
                        raise ValueError('OSM export lacks stable feature identity')
                    if identity.startswith('relation/'):
                        accepted_relations[identity] = buildings
                    for component,building in enumerate(buildings):
                        ring = building['ring_rad'][:-1]
                        lon = math.degrees(sum(p[0] for p in ring)/len(ring))
                        lat = math.degrees(sum(p[1] for p in ring)/len(ring))
                        col = min(columns-1,int((lon-west)/(east-west)*columns))
                        row = min(rows-1,int((lat-south)/(north-south)*rows))
                        buckets[row,col][f'{identity}#{component}'] = building
            except BaseException:
                process.terminate()
                raise
            finally:
                process.stdout.close()
                code = process.wait()
            if code:
                raise RuntimeError(f'osmium export failed ({code})')
        # Remove only identical outer-member ways of accepted relations. Keep a
        # height-informed way if its parent has no usable height metadata.
        candidates = {}
        for identity,components in accepted_relations.items():
            for way in members.get(identity,()):
                candidates.setdefault(way,[]).extend(components)
        for bucket in buckets.values():
            for identity,building in list(bucket.items()):
                parents = candidates.get(identity.rsplit('#',1)[0],())
                if any(ring_identity(parent['ring_rad']) == ring_identity(building['ring_rad'])
                       and parent.get('is_part',False) == building.get('is_part',False)
                       and (parent['height_source'] != 'placeholder' or building['height_source'] == 'placeholder')
                       for parent in parents):
                    del bucket[identity]
                    duplicates += 1
        part_outlines = mark_part_outlines(buckets)
        if not any(buckets.values()):
            raise ValueError('No supported building outlines in selected coverage; verify your source region')
        pack = scratch/'pack'
        pack.mkdir()
        records = []
        for tile_id,tile_bounds,features,content in partition_buildings(
                buckets,bounds,rows,columns,adaptive=preset == 'metro-detroit'):
            local = pack/tile_id
            local.mkdir()
            for building in features:
                height_counts[building['height_source']] += 1
            (local/'buildings.json').write_bytes(content)
            records.append({'id':tile_id,'title':title,'attribution':CREDIT,
                'bounds_deg':tile_bounds,
                'buildings_count':len(features),'sha256':{'buildings.json':digest(local/'buildings.json')}})
        manifest = {'schema':3,'title':title+' buildings','attribution':CREDIT,'bounds_deg':bounds,
            'tiles':records,'layers':['buildings'],'generated_utc':datetime.now(timezone.utc).isoformat(),
            'license':'https://opendatacommons.org/licenses/odbl/1-0/', 'skipped_features':skipped,
            'height_counts':height_counts, 'grid':[rows,columns],
            'part_components':sum(bool(b.get('is_part')) for cell in buckets.values() for b in cell.values()),
            'outlines_with_parts':part_outlines,
            'relation_components':sum(len(parts) for parts in accepted_relations.values()),
            'courtyard_components':sum(bool(b.get('holes_rad')) for cell in buckets.values() for b in cell.values()),
            'duplicate_member_ways_removed':duplicates,
            'sources':[{'file':source.name,'sha256':digest(source)} for source in sources]}
        (pack/'manifest.json').write_text(json.dumps(manifest,indent=2))
        validate_pack(pack)
        pack.rename(destination)
    return destination


def validate_pack(directory):
    root = Path(directory).resolve()
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    terrain_only = manifest.get('layers') == ['terrain']
    if manifest.get('schema') not in (1,2,3) or not 0 <= len(manifest['tiles']) <= MAX_MAP_TILES or (not manifest['tiles'] and not terrain_only):
        raise ValueError('Unsupported 3D pack schema')
    west,south,east,north = manifest['bounds_deg']
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('Invalid 3D coverage')
    seen,checksums,total = set(),{'manifest.json':digest(manifest_path)},0
    layers = set() if terrain_only else {'buildings'}
    if terrain_only:
        if manifest['tiles']:
            raise ValueError('Terrain-only pack cannot contain building tiles')
        from .terrain import validate_terrain
        validate_terrain(root)
        layers.add('terrain')
    for tile in manifest['tiles']:
        key = tile['id']
        if not re.fullmatch(r'[a-z0-9-]{1,32}',key) or key in seen:
            raise ValueError('Invalid/duplicate 3D tile identifier')
        seen.add(key)
        w,s,e,n = tile['bounds_deg']
        if not (west <= w < e <= east and south <= s < n <= north):
            raise ValueError('3D tile outside pack coverage')
        if set(tile['sha256']) not in ({'buildings.json'},{'buildings.json','imagery.jpg'}):
            raise ValueError('Unsupported 3D assets')
        for name,expected in tile['sha256'].items():
            file = (root/key/name).resolve()
            limit = (20 if name=='imagery.jpg' else 10)*1024*1024
            if not file.is_relative_to(root) or not file.is_file() or file.stat().st_size > limit:
                raise ValueError('3D asset outside pack, missing or oversized')
            actual = digest(file)
            if actual != expected:
                raise ValueError('3D asset checksum mismatch')
            checksums[f'{key}/{name}'] = actual
            if name=='imagery.jpg':
                layers.add('imagery')
        data = json.loads((root/key/'buildings.json').read_text())
        if not data.get('attribution') or len(data['buildings']) != tile['buildings_count'] or len(data['buildings']) > 10000:
            raise ValueError('Building attribution/count mismatch')
        for building in data['buildings']:
            LocalBuilding.from_document(building)
        total += len(data['buildings'])
    for file in root.rglob('*'):
        if file.is_file():
            if not file.resolve().is_relative_to(root):
                raise ValueError('3D provenance asset outside pack')
            checksums[str(file.relative_to(root))] = digest(file)
    return {'title':manifest['title'],'bounds_deg':manifest['bounds_deg'],'layers':sorted(layers),
            'tiles':len(seen),'buildings':total,'bytes':sum(p.stat().st_size for p in root.rglob('*') if p.is_file()),
            'checksums':checksums}


def validate_packs(root):
    directory = Path(root)/'maps/3d/packs'
    result = {}
    if directory.exists():
        for pack in sorted(directory.iterdir()):
            if pack.name.startswith('.'):
                continue
            if not pack.is_dir() or not re.fullmatch(r'[a-z0-9-]{1,64}',pack.name):
                raise ValueError('Invalid 3D pack directory')
            result[pack.name] = validate_pack(pack)
    return result
