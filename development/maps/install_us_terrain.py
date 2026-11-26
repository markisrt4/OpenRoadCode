"""Verify downloaded US terrain packs and atomically activate a paged catalog."""
import argparse
import json
import uuid
from pathlib import Path

from apps.launchers.local_terrain_pack import load_terrain
from common.xdg_paths import openroadcode_data_dir
from development.maps.install_terrain import _install_archive
from development.maps.prebuilt_imagery import read_local_archive
from development.maps.state_map_catalog import catalog_document
from tools.map_builder.builder.terrain_artifact import MAX_ARCHIVE_BYTES


def install(directory, *, destination=None, allow_partial=False):
    root = destination or openroadcode_data_dir('map-packs', 'us-terrain')
    definitions = {region['coverage']: (state['abbreviation'], region['bounds_deg'])
                   for state in catalog_document()['states'] for region in state['overview_regions']}
    expected = {key for key, (state, _) in definitions.items() if state not in ('AK', 'HI')}
    archives = {}
    for path in Path(directory).rglob('*-terrain.zip'):
        key = path.name.removesuffix('-terrain.zip')
        if key not in definitions:
            continue
        descriptor, archive = read_local_archive(path, key, max_archive_bytes=MAX_ARCHIVE_BYTES)
        if descriptor.get('kind') != 'terrain' or descriptor.get('bounds_deg') != list(definitions[key][1]):
            raise ValueError('Wrong terrain kind or coverage: '+key)
        if key in archives:
            if archives[key][0]['sha256'] != descriptor['sha256']:
                raise ValueError('Conflicting national terrain archives: '+key)
            continue
        archives[key] = (descriptor, archive)
    if not archives or (not allow_partial and expected-set(archives)):
        raise ValueError('Expected all 48 continental states; missing '+', '.join(sorted(expected-set(archives))))
    root.mkdir(parents=True, exist_ok=True)
    if (root/'active').exists() and not (root/'active').is_symlink():
        raise ValueError('National active catalog must be a managed link')
    previous = root/'active/catalog.json'
    old = json.loads(previous.read_text()) if previous.is_file() else {}
    rows = list(old.get('tiles', [])); states = set(old.get('states', []))
    for number, (key, (descriptor, archive)) in enumerate(sorted(archives.items()), 1):
        revision = root/'packs'/(key+'-'+descriptor['sha256'])
        if not revision.exists():
            _install_archive(archive, revision, expected_bounds=definitions[key][1])
        state = load_terrain(revision)
        rows = [row for row in rows if not row['id'].startswith(key+'--')]
        manifest = json.loads((revision/'manifest.json').read_text())
        if not hasattr(state, 'tiles'):
            raise ValueError('National baseline requires a validated terrain mosaic')
        for index, (tile, record) in enumerate(zip(state.tiles, manifest['tiles'], strict=True)):
            rows.append(dict(id=key+'--'+str(index), path=str((revision/record['path']).relative_to(root)),
                             sha256=record['sha256'], bounds_deg=record['bounds_deg'],
                             width=tile.width, height=tile.height, datum=tile.vertical_datum))
        states.add(definitions[key][0])
        print(f'Install: {number}/{len(archives)} packs · {number*100/len(archives):.0f}%', flush=True)
    if len(rows) > 4096:
        raise ValueError('National terrain index exceeds 4096 grids')
    snapshot = root/('catalog-'+uuid.uuid4().hex)
    snapshot.mkdir()
    (snapshot/'catalog.json').write_text(json.dumps(dict(schema=1, kind='us-terrain-index', states=sorted(states), tiles=rows)))
    pending = root/('.active-'+uuid.uuid4().hex)
    pending.symlink_to(snapshot.name, target_is_directory=True)
    try:
        pending.replace(root/'active')
    finally:
        pending.unlink(missing_ok=True)
    print(f'Ready: {len(states)} states, {len(rows)} paged grids. Reopen Terrain. Existing regional detail takes priority.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--allow-partial', action='store_true')
    args = parser.parse_args()
    try:
        install(args.directory, allow_partial=args.allow_partial)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'US terrain install failed: {error}\n')


if __name__ == '__main__':
    main()
