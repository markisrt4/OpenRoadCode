"""Verify downloaded statewide cells and atomically activate their small catalog."""
import argparse
import json
from pathlib import Path
import uuid

from apps.launchers.local_imagery_pyramid import LocalImageryPyramidPack
from apps.launchers.local_terrain_pack import load_terrain
from common.xdg_paths import openroadcode_data_dir
from development.maps.prebuilt_imagery import read_local_archive,unpack
from development.maps.statewide_detail_plan import PROFILE,MAX_CELL_ARCHIVE,parse_cell,bounds


def validate_cell(root,expected_key=None):
    manifest=json.loads((root/'manifest.json').read_text())
    if (manifest.get('profile')!=PROFILE or manifest.get('kind')!='michigan-detail-cell'
            or (expected_key is not None and manifest.get('id')!=expected_key)):
        raise ValueError('Wrong statewide detail profile')
    if manifest.get('imagery_available'):
        image=LocalImageryPyramidPack.load(root/'imagery')
        if image.state.maximum_zoom!=16:raise ValueError('Wrong statewide imagery zoom profile')
        child=json.loads((root/'imagery/manifest.json').read_text())
        if child['bounds_deg']!=manifest['bounds_deg']:raise ValueError('Imagery detail cell bounds mismatch')
    if manifest.get('terrain_available'):
        load_terrain(root/'terrain')
        child=json.loads((root/'terrain/manifest.json').read_text())
        if child['bounds_deg']!=manifest['bounds_deg']:raise ValueError('Terrain detail cell bounds mismatch')


def install(directory,*,allow_partial=False,destination=None):
    directory=Path(directory)
    plans=list(directory.rglob('statewide-plan.json'))
    if len(plans)!=1:raise ValueError('Expected one statewide-plan.json artifact')
    plan=json.loads(plans[0].read_text())
    if plan.get('profile')!=PROFILE:raise ValueError('Unexpected statewide detail plan profile')
    expected={c['id']:c for c in plan['cells']}
    if not 1<=len(expected)<=768:raise ValueError('Invalid statewide cell count')
    for key,cell in expected.items():
        x,y=parse_cell(key)
        if any(abs(a-b)>1e-9 for a,b in zip(cell['bounds_deg'],bounds(x,y))):
            raise ValueError('Detail plan bounds mismatch')
    available={};descriptors={}
    # No active pointers change until every supplied archive passes preflight.
    for key in expected:
        files=list(directory.rglob(key+'.zip'))
        if len(files)>1:raise ValueError(f'Duplicate cell archive: {key}')
        if files:
            descriptor,archive=read_local_archive(files[0],key,max_archive_bytes=MAX_CELL_ARCHIVE)
            if descriptor.get('profile')!=PROFILE or descriptor.get('kind')!='michigan-detail-cell':
                raise ValueError('Wrong statewide detail cell descriptor')
            available[key]=archive;descriptors[key]=descriptor
    if not available or (not allow_partial and len(available)!=len(expected)):
        raise ValueError(f'Found {len(available)}/{len(expected)} cells; finish downloads or use --allow-partial')
    root=destination or openroadcode_data_dir('map-packs','michigan-detail')
    cells=root/'cells';cells.mkdir(parents=True,exist_ok=True)
    if (root/'active').exists() and not (root/'active').is_symlink():
        raise ValueError('Detail active catalog must be a managed link')
    current=root/'active/catalog.json'
    rows={r['id']:r for r in json.loads(current.read_text())['cells']} if current.is_file() else {}
    for number,(key,archive) in enumerate(available.items(),1):
        descriptor=descriptors[key];revision=cells/(key+'-'+descriptor['sha256'])
        if not revision.exists():
            unpack(archive,revision,expected[key]['bounds_deg'],loader=lambda path:validate_cell(path,key),
                   max_unpacked_bytes=2*1024**3+128*1024**2)
        else:validate_cell(revision,key)
        rows[key]=dict(id=key,sha256=descriptor['sha256'])
        print(f'Detail install: {number}/{len(available)} cells · {number*100/len(available):.0f}%',flush=True)
    snapshot=root/('catalog-'+uuid.uuid4().hex);snapshot.mkdir()
    (snapshot/'catalog.json').write_text(json.dumps(dict(schema=1,profile=PROFILE,cells=list(rows.values()))))
    pending=root/('.active-'+uuid.uuid4().hex);pending.symlink_to(snapshot.name,target_is_directory=True)
    try:pending.replace(root/'active')
    finally:pending.unlink(missing_ok=True)
    print(f'Ready: {len(rows)}/{len(expected)} statewide detail cells. Reopen Terrain.')
    return root/'active'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--allow-partial',action='store_true');args=parser.parse_args()
    try:install(args.directory,allow_partial=args.allow_partial)
    except (OSError,ValueError,KeyError,RuntimeError) as error:parser.exit(1,f'Statewide detail install failed: {error}\n')


if __name__=='__main__':main()
