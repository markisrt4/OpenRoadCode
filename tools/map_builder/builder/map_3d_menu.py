"""Terminal choices for optional 3D data; no rendering or acquisition policy."""
from .map_3d import PRESETS


def choose_coverage(layer='buildings'):
    print('\nOptional offline 3D map packs')
    if layer == 'terrain':
        print('Terrain: USGS 3DEP ground samples, downloaded now for offline viewing.')
    else:
        print('Available: building footprints and tagged/estimated heights from installed OSM sources.')
        print('Terrain: run 3d --layer terrain for a separate USGS 3DEP offline pack. Imagery build is not available here yet.')
    keys = list(PRESETS)
    for index,key in enumerate(keys,1):
        title,bounds = PRESETS[key]
        print(f'  {index}. {title} · bounds {bounds}')
    while True:
        choice = input(f'Choose coverage [{"/".join(str(i) for i in range(1, len(keys)+1))}, Enter cancels]: ').strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(keys):
            return keys[int(choice)-1]
        print('Choose one of the listed numbers.')


def select_install_packs(manifest):
    """Return optional pack IDs; cancellation makes no installation changes."""
    packs = manifest.get('map_3d') or manifest.get('validation',{}).get('map_3d',{})
    print('\nNavigation data install')
    print('Regions: '+', '.join(str(r.get('name',r.get('id','unknown'))) for r in manifest.get('regions',[])))
    print('Base map/search/routing data are installed together.')
    if isinstance(manifest.get('deployable_bytes'),int):
        base_bytes = manifest['deployable_bytes']-sum(record['bytes'] for record in packs.values())
        print(f'Base dataset payload: {max(0,base_bytes)/1024/1024:.2f} MiB (before selected 3D packs)')
    else:
        print('Base dataset size is unavailable in this older manifest.')
    selected = []
    for key,record in sorted(packs.items()):
        print(f"\n{record['title']} · {', '.join(record['layers'])} · {record['bytes']/1024/1024:.2f} MiB")
        print(f"Coverage: {record['bounds_deg']} · {record['buildings']} buildings")
        if input('Include this optional 3D pack? [y/N] ').strip().lower() == 'y':
            selected.append(key)
    if input('\nInstall this selection now? [y/N] ').strip().lower() != 'y':
        return None
    return selected
