"""Package an already validated imagery pack for ordinary file distribution."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from apps.launchers.local_imagery_pack import LocalImageryPack
from development.maps.terrain_regions import MICHIGAN_COVERAGES

MAX_ARCHIVE_BYTES = 64*1024*1024


def package(root, output, coverage):
    root, output = Path(root).resolve(), Path(output).resolve()
    pack = LocalImageryPack.load(root)
    if output.is_relative_to(root):
        raise ValueError('Write the archive outside the source pack')
    files = sorted(path for path in root.rglob('*') if path.is_file())
    if (len(files) > 2048 or any(path.is_symlink() or not path.resolve().is_relative_to(root) for path in files)
            or sum(path.stat().st_size for path in files) > MAX_ARCHIVE_BYTES):
        raise ValueError('Imagery artifact exceeds file limits or contains links')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name+'.tmp')
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(root).as_posix())
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError('Imagery archive exceeds 64 MiB')
        with temporary.open('rb') as source:
            digest = hashlib.file_digest(source, 'sha256').hexdigest()
        descriptor = {'schema':1, 'coverage':coverage, 'title':pack.state.title,
                      'archive':output.name, 'bytes':temporary.stat().st_size, 'sha256':digest,
                      'bounds_deg':json.loads((root/'manifest.json').read_text())['bounds_deg']}
        temporary.replace(output)
        output.with_suffix(output.suffix+'.json').write_text(json.dumps(descriptor, indent=2))
        return descriptor
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--coverage', choices=('metro-detroit','detroit-midtown','rochester','southfield',
                                               *MICHIGAN_COVERAGES), required=True)
    args = parser.parse_args()
    try:
        descriptor = package(args.pack, args.output, args.coverage)
        print(f"Ready: {args.output} · {descriptor['bytes']:,} bytes · SHA256 {descriptor['sha256']}")
        print('Distribute the archive and adjacent .zip.json together. No upload was performed.')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Imagery packaging failed: {error}\n')


if __name__ == '__main__':
    main()
