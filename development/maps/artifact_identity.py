"""Stable identities for reusable offline map-data artifacts."""

import argparse
import hashlib
import json
from pathlib import Path


_REVISIONS = {
    "imagery": "usgs-naip-default-mosaic-nodata24-v1",
    "terrain": "usgs-3dep-tiled-grid-v1",
}

_MICHIGAN_COVERAGES = frozenset({
    'michigan-overview', 'mi-lower-southwest', 'mi-lower-southeast',
    'mi-lower-central-west', 'mi-lower-central-east', 'mi-lower-northwest',
    'mi-lower-northeast', 'mi-upper-west', 'mi-upper-east',
})


def build_revision(kind):
    """Return the reviewed input/algorithm revision for one artifact kind."""
    try:
        return _REVISIONS[kind]
    except KeyError as error:
        raise ValueError(f"Unsupported map artifact kind: {kind}") from error


def build_profile(kind, coverage):
    """Return output dimensions/layout that participate in reuse identity."""
    if kind == 'imagery':
        return ('8192x8192' if coverage in _MICHIGAN_COVERAGES
                or coverage.endswith('-overview') or '-detail-' in coverage
                else '4096x4096-detail')
    if kind == 'terrain':
        return 'staged-3dep-10m-class-endpoint129-v1' if coverage.endswith('-detail-10m') else 'coverage-defined-tiled-grid'
    raise ValueError(f"Unsupported map artifact kind: {kind}")


def build_fingerprint(kind, coverage):
    """Identify outputs without coupling map data to unrelated source commits."""
    if not coverage or any(character.isspace() for character in coverage):
        raise ValueError("Coverage must be a non-empty normalized identifier")
    identity = (f"openroadcode-map-data\0{kind}\0{coverage}\0{build_profile(kind, coverage)}"
                f"\0{build_revision(kind)}")
    return hashlib.sha256(identity.encode()).hexdigest()


def validate_descriptor(path, kind, coverage):
    """Reject a release descriptor that was produced by different build inputs."""
    document = json.loads(Path(path).read_text())
    expected = build_fingerprint(kind, coverage)
    expected_archive = f"{coverage}-{kind}.zip"
    if (document.get("schema") != 1 or document.get("kind") != kind
            or document.get("coverage") != coverage
            or document.get("archive") != expected_archive
            or document.get("build_profile") != build_profile(kind, coverage)
            or document.get("build_revision") != build_revision(kind)
            or document.get("build_fingerprint") != expected
            or not isinstance(document.get("bytes"), int) or document["bytes"] <= 0
            or len(document.get("sha256", "")) != 64):
        raise ValueError(f"Existing {kind} descriptor does not match {coverage} build inputs")
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=tuple(_REVISIONS))
    parser.add_argument("coverage")
    parser.add_argument("--descriptor", type=Path)
    args = parser.parse_args()
    if args.descriptor:
        validate_descriptor(args.descriptor, args.kind, args.coverage)
        print(f"Reusable {args.kind} descriptor: {args.descriptor}")
    else:
        print(build_fingerprint(args.kind, args.coverage))


if __name__ == "__main__":
    main()
