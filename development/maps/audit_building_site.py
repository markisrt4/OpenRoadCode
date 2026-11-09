"""Explain how existing OSM extraction/height rules affect the Chrysler campus."""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from development.maps.build_regional_buildings import michigan_region
from development.maps.state_map_catalog import _coordinates
from tools.map_builder.builder.build import _download_and_verify
from tools.map_builder.builder.geofabrik import fetch_index
from tools.map_builder.builder.map_3d import normalize_components, PRESETS, height, digest

SITE_BOUNDS = (-83.26,42.635,-83.21,42.67)


def classify(feature):
    properties = feature.get('properties') or {}
    geometry = feature.get('geometry') or {}
    points = tuple(_coordinates(geometry.get('coordinates', [])))
    if not points:
        return None
    bounds = (min(p[0] for p in points),min(p[1] for p in points),
              max(p[0] for p in points),max(p[1] for p in points))
    identity = str(feature.get('id') or '')
    if properties.get('building') in (None,'no') and properties.get('building:part'):
        reason = 'building part excluded by current building-way filter'
    elif not normalize_components(feature,PRESETS['metro-detroit'][1]):
        reason = 'complex footprint or unsupported geometry excluded'
    elif height(properties)[1] == 'placeholder':
        reason = 'accepted footprint without height/floor tags; placeholder hidden'
    else:
        reason = 'accepted height-informed footprint; visibility/zoom must still be checked'
    return dict(id=identity,name=properties.get('name',''),geometry=geometry.get('type'),
                bounds_deg=bounds,height_m=height(properties)[0],height_source=height(properties)[1],
                tags={key:properties[key] for key in ('building','building:part','height','building:levels','min_height') if key in properties},
                reason=reason,rank=(bounds[2]-bounds[0])*(bounds[3]-bounds[1]))


def audit(output, cache):
    output.mkdir(parents=True,exist_ok=True)
    candidates = sorted((cache/'pbf').glob('*.osm.pbf'))
    if candidates:
        source = candidates[0]
    else:
        source = _download_and_verify(michigan_region(fetch_index(cache/'geofabrik-index.json')),cache_root=cache)
    with TemporaryDirectory(dir=output,prefix='.site-audit-') as temporary:
        root = Path(temporary)
        extract,filtered = root/'site.osm.pbf',root/'buildings.osm.pbf'
        subprocess.run(['osmium','extract','-b',','.join(map(str,SITE_BOUNDS)),
                        '-s','smart','-S','types=multipolygon',str(source),'-o',str(extract)],check=True)
        subprocess.run(['osmium','tags-filter',str(extract),'wr/building','wr/building:part',
                        '-o',str(filtered)],check=True)
        command = ['osmium','export',str(filtered),'--geometry-types=polygon',
                   '--add-unique-id=type_id','--attributes=type,id','-f','geojsonseq','-o','-']
        rows = []
        with subprocess.Popen(command,stdout=subprocess.PIPE,text=True) as process:
            for line in process.stdout:
                if not line.strip():
                    continue
                row = classify(json.loads(line.lstrip('\x1e')))
                if row:
                    rows.append(row)
            if process.wait():
                raise RuntimeError('OSM building audit export failed')
    rows.sort(key=lambda row:row['rank'],reverse=True)
    report = dict(site='Chrysler Technology Center / Auburn Hills vicinity',bounds_deg=SITE_BOUNDS,
        source_sha256=digest(source),attribution='© OpenStreetMap contributors · ODbL 1.0',
        classifications=dict(Counter(row['reason'] for row in rows)),largest_features=rows[:20])
    (output/'building-site-audit.json').write_text(json.dumps(report,indent=2))
    print('Building site audit: '+json.dumps(report,sort_keys=True),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    args = parser.parse_args()
    audit(args.output,args.cache)


if __name__ == '__main__':
    main()
