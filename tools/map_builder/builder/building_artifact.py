"""Package checked OSM building tiles for the existing offline tile reader."""

import json
from pathlib import Path
import zipfile

from .map_3d import digest, validate_pack

MAX_ARCHIVE_BYTES = 128*1024*1024

MAX_UNPACKED_BYTES = 512*1024*1024


def package(root, output, coverage):
    root, output = Path(root).resolve(), Path(output).resolve()
    validated = validate_pack(root)
    files = sorted(path for path in root.rglob('*') if path.is_file())
    if (output.is_relative_to(root) or len(files) > 2048
            or validated['bytes'] > MAX_UNPACKED_BYTES
            or any(path.is_symlink() or not path.resolve().is_relative_to(root) for path in files)):
        raise ValueError('Building archive layout or extraction size exceeds limits')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.zip.part')
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.write(path, path.relative_to(root).as_posix())
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError('Building archive exceeds 128 MiB download limit')
        manifest = json.loads((root/'manifest.json').read_text())
        descriptor = dict(schema=1, kind='buildings', coverage=coverage, archive=output.name,
            bytes=temporary.stat().st_size, sha256=digest(temporary), bounds_deg=validated['bounds_deg'],
            buildings=validated['buildings'], tiles=validated['tiles'],
            height_counts=manifest.get('height_counts', {}),
            license='ODbL-1.0', license_url='https://opendatacommons.org/licenses/odbl/1-0/')
        temporary.replace(output)
        output.with_suffix(output.suffix+'.json').write_text(json.dumps(descriptor, indent=2))
        return descriptor
    finally:
        temporary.unlink(missing_ok=True)
