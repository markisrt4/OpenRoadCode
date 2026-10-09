"""Selection and validation helpers for existing navigation-data pull scripts."""
import argparse
import json
from pathlib import Path
import re
import shutil

from .map_3d import validate_pack
from .map_3d_menu import select_install_packs


def catalog(manifest):
    packs = manifest.get('map_3d') or manifest.get('validation',{}).get('map_3d',{})
    if not isinstance(packs,dict) or any(not re.fullmatch(r'[a-z0-9-]{1,64}',key) for key in packs):
        raise ValueError('Invalid optional 3D pack catalog')
    return packs


def validate_selection(root, selection):
    root = Path(root)
    manifest = json.loads((root/'build-manifest.json').read_text())
    available = catalog(manifest)
    for key in selection:
        if key not in available:
            raise ValueError('Selected 3D pack absent from dataset manifest')
        actual = validate_pack(root/'maps/3d/packs'/key)
        expected = available[key]
        if actual != expected:
            raise ValueError(f'3D pack does not match build certificate: {key}')
    installed = root/'maps/3d/packs'
    if installed.exists():
        actual_ids = {p.name for p in installed.iterdir() if not p.name.startswith('.')}
        if actual_ids != set(selection):
            raise ValueError('Unexpected or missing optional 3D pack')


def prepare_staging(root, selection):
    root = Path(root).resolve()
    packs = root/'maps/3d/packs'
    if packs.exists():
        if not packs.resolve().is_relative_to(root):
            raise ValueError('Staged pack directory escapes staging root')
        for pack in packs.iterdir():
            if pack.name not in selection:
                if pack.is_symlink() or pack.is_file():
                    pack.unlink()
                elif pack.is_dir():
                    shutil.rmtree(pack)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    choose = sub.add_parser('choose')
    choose.add_argument('--manifest',type=Path,required=True)
    choose.add_argument('--selection',type=Path,required=True)
    choose.add_argument('--all',action='store_true')
    validate = sub.add_parser('validate')
    validate.add_argument('--root',type=Path,required=True)
    validate.add_argument('--selection',type=Path,required=True)
    stage = sub.add_parser('stage')
    stage.add_argument('--root',type=Path,required=True)
    stage.add_argument('--selection',type=Path,required=True)
    args = parser.parse_args()
    try:
        if args.command == 'choose':
            manifest = json.loads(args.manifest.read_text())
            available = catalog(manifest)
            selected = sorted(available) if args.all else select_install_packs(manifest)
            if selected is None:
                print('Cancelled; installed data unchanged.')
                return 3
            args.selection.write_text(json.dumps({'packs':selected}))
            # Pull scripts consume this list as literal rsync include patterns.
            for key in selected:
                print(key)
            return 0
        selection = json.loads(args.selection.read_text())['packs']
        if args.command == 'stage':
            prepare_staging(args.root,selection)
            return 0
        validate_selection(args.root,selection)
        print(f'Validated {len(selection)} optional 3D packs')
        return 0
    except (EOFError,KeyboardInterrupt):
        print('Cancelled; installed data unchanged.')
        return 3
    except (OSError,ValueError,KeyError,TypeError) as error:
        parser.exit(1,f'3D data install: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
