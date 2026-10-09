"""Optional offline building packs from existing OSM sources; no service queries."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

PRESETS = {
    'detroit-downtown': ('Detroit Downtown',(-83.065,42.315,-83.025,42.345)),
    'detroit-midtown': ('Detroit Downtown–Midtown',(-83.085,42.315,-83.025,42.375)),
}
CREDIT = '© OpenStreetMap contributors · ODbL 1.0'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def height(tags):
    for key,source,scale in (('height','osm-height',1),('building:levels','levels-estimate',3)):
        try:
            value = float(str(tags.get(key,'')).strip().removesuffix(' m'))*scale
            if math.isfinite(value) and 1 <= value <= 1000:
                return value,source
        except ValueError:
            pass
    return 9.0,'placeholder'


def normalize(feature,bounds):
    tags = feature.get('properties') or {}
    if tags.get('building') in (None,'no'):
        return None
    geometry = feature.get('geometry') or {}
    rings = geometry.get('coordinates') or []
    # Courtyards and multipolygons require a richer geometry contract later.
    if geometry.get('type') != 'Polygon' or len(rings) != 1:
        return None
    ring = rings[0]
    if not 4 <= len(ring) <= 2000 or ring[0] != ring[-1]:
        return None
    west,south,east,north = bounds
    if any(len(p) < 2 or not (west <= p[0] <= east and south <= p[1] <= north) for p in ring):
        return None
    h,source = height(tags)
    return {'ring_rad':[[math.radians(p[0]),math.radians(p[1])] for p in ring],
            'height_m':h,'height_source':source}


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
    buckets = {(row,col):{} for row in range(4) for col in range(2)}
    skipped = 0
    with TemporaryDirectory(dir=destination.parent,prefix='.build-3d-') as temporary:
        scratch = Path(temporary)
        for index,source in enumerate(sources):
            extract,filtered = scratch/f'{index}.osm.pbf',scratch/f'{index}-buildings.osm.pbf'
            subprocess.run(['osmium','extract','-b',','.join(map(str,bounds)),'-s','complete_ways',
                            str(source),'-o',str(extract)],check=True)
            subprocess.run(['osmium','tags-filter',str(extract),'w/building','-o',str(filtered)],check=True)
            command = ['osmium','export',str(filtered),'--geometry-types=polygon',
                       '--add-unique-id=type_id','--attributes=type,id','-f','geojsonseq','-o','-']
            process = subprocess.Popen(command,stdout=subprocess.PIPE,text=True)
            try:
                for line in process.stdout:
                    if not line.strip():
                        continue
                    feature = json.loads(line.lstrip('\x1e'))
                    building = normalize(feature,bounds)
                    if building is None:
                        skipped += 1
                        continue
                    ring = building['ring_rad'][:-1]
                    lon = math.degrees(sum(p[0] for p in ring)/len(ring))
                    lat = math.degrees(sum(p[1] for p in ring)/len(ring))
                    col = min(1,int((lon-west)/(east-west)*2))
                    row = min(3,int((lat-south)/(north-south)*4))
                    props = feature.get('properties') or {}
                    identity = feature.get('id') or f"{props.get('@type')}:{props.get('@id')}"
                    if identity == 'None:None':
                        raise ValueError('OSM export lacks stable feature identity')
                    buckets[row,col][str(identity)] = building
            except BaseException:
                process.terminate()
                raise
            finally:
                process.stdout.close()
                code = process.wait()
            if code:
                raise RuntimeError(f'osmium export failed ({code})')
        if not any(buckets.values()):
            raise ValueError('No simple building outlines in selected coverage; verify your source region')
        pack = scratch/'pack'
        pack.mkdir()
        records = []
        for (row,col),features in buckets.items():
            tile_id = f'r{row}-c{col}'
            local = pack/tile_id
            local.mkdir()
            content = json.dumps({'attribution':CREDIT,'buildings':list(features.values())}).encode()
            if len(content) > 10*1024*1024 or len(features) > 10000:
                raise ValueError('Building tile exceeds runtime limits')
            (local/'buildings.json').write_bytes(content)
            records.append({'id':tile_id,'title':title,'attribution':CREDIT,
                'bounds_deg':[west+(east-west)*col/2,south+(north-south)*row/4,
                              west+(east-west)*(col+1)/2,south+(north-south)*(row+1)/4],
                'buildings_count':len(features),'sha256':{'buildings.json':digest(local/'buildings.json')}})
        manifest = {'schema':1,'title':title+' buildings','attribution':CREDIT,'bounds_deg':bounds,
            'tiles':records,'layers':['buildings'],'generated_utc':datetime.now(timezone.utc).isoformat(),
            'license':'https://opendatacommons.org/licenses/odbl/1-0/', 'skipped_features':skipped,
            'sources':[{'file':source.name,'sha256':digest(source)} for source in sources]}
        (pack/'manifest.json').write_text(json.dumps(manifest,indent=2))
        validate_pack(pack)
        pack.rename(destination)
    return destination


def validate_pack(directory):
    root = Path(directory).resolve()
    manifest_path = root/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schema') != 1 or not 1 <= len(manifest['tiles']) <= 32:
        raise ValueError('Unsupported 3D pack schema')
    west,south,east,north = manifest['bounds_deg']
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('Invalid 3D coverage')
    seen,checksums,total = set(),{'manifest.json':digest(manifest_path)},0
    layers = {'buildings'}
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
            ring = building['ring_rad']
            if not 4 <= len(ring) <= 2000 or ring[0] != ring[-1]:
                raise ValueError('Invalid building ring')
            if any(len(p)!=2 or not (-math.pi <= p[0] <= math.pi and -math.pi/2 <= p[1] <= math.pi/2) for p in ring):
                raise ValueError('Invalid building coordinates')
            if not 1 <= building['height_m'] <= 1000 or building['height_source'] not in ('osm-height','levels-estimate','placeholder'):
                raise ValueError('Invalid building height')
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
