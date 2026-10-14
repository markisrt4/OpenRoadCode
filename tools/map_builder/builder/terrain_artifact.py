"""Package a validated terrain mosaic as a checksummed release asset."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from apps.launchers.local_terrain_pack import load_terrain

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024


def package(root, output, coverage):
    root, output = Path(root).resolve(), Path(output).resolve()
    load_terrain(root)
    files = sorted(path for path in root.rglob("*") if path.is_file())
    if output.is_relative_to(root) or len(files) > 4096:
        raise ValueError("Invalid terrain artifact layout")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                if path.is_symlink() or not path.resolve().is_relative_to(root):
                    raise ValueError("Terrain artifact contains an unsafe path")
                archive.write(path, path.relative_to(root).as_posix())
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError("Terrain archive exceeds 64 MiB")
        with temporary.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        descriptor = {
            "schema": 1,
            "kind": "terrain",
            "coverage": coverage,
            "archive": output.name,
            "bytes": temporary.stat().st_size,
            "sha256": digest,
            "bounds_deg": json.loads((root / "manifest.json").read_text())["bounds_deg"],
        }
        temporary.replace(output)
        output.with_suffix(output.suffix + ".json").write_text(json.dumps(descriptor, indent=2))
        return descriptor
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--coverage", default="metro-detroit")
    args = parser.parse_args()
    package(args.pack, args.output, args.coverage)


if __name__ == "__main__":
    main()
