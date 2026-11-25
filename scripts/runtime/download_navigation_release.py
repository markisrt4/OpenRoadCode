#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Download and safely stage a catalogued navigation release."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tarfile
from pathlib import Path


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(url: str, path: Path, expected: str | None = None) -> None:
    if path.is_file() and expected and digest(path) == expected:
        return
    partial = path.with_name(path.name + ".partial")
    if not expected:
        partial.unlink(missing_ok=True)
    subprocess.run(
        [
            "curl", "--fail", "--location", "--retry", "5",
            "--connect-timeout", "20", "--continue-at", "-",
            "--output", str(partial), url,
        ],
        check=True,
    )
    if expected and digest(partial) != expected:
        partial.unlink()
        raise ValueError(f"Checksum mismatch: {path.name}")
    partial.replace(path)


def parse_checksums(path: Path, names: list[str]) -> dict[str, str]:
    checksums = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([a-fA-F0-9]{64}) [ *]([^/]+)", line)
        if not match or match[2] not in names or match[2] in checksums:
            raise ValueError(f"Unexpected checksum entry: {line}")
        checksums[match[2]] = match[1].lower()
    if set(checksums) != set(names):
        raise ValueError("Release checksum list is incomplete")
    return checksums


def extract(parts: list[Path], stage: Path) -> None:
    if stage.exists():
        raise ValueError("Extraction destination must not exist")
    stage.mkdir(parents=True)
    try:
        # Stream split archives through tar without creating a second large file.
        with subprocess.Popen(
            ["cat", *(str(part) for part in parts)], stdout=subprocess.PIPE
        ) as process:
            assert process.stdout is not None
            try:
                with tarfile.open(fileobj=process.stdout, mode="r|gz") as archive:
                    for member in archive:
                        if not (member.isfile() or member.isdir()):
                            raise ValueError(f"Unsupported archive entry: {member.name}")
                        archive.extract(member, stage, filter="data")
                # Drain any remaining compressed bytes before waiting for cat.
                while process.stdout.read(1024 * 1024):
                    pass
                if process.wait():
                    raise RuntimeError("Failed to read archive parts")
            except BaseException:
                process.kill()
                raise
    except BaseException:
        shutil.rmtree(stage)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--stage", required=True, type=Path)
    parser.add_argument("--manifest-only", action="store_true")
    args = parser.parse_args()
    catalog = json.loads(
        Path(__file__).with_name("navigation-data-catalog.json").read_text(
            encoding="utf-8"
        )
    )
    entry = catalog["regions"][args.region]
    cache = args.cache / entry["tag"]
    cache.mkdir(parents=True, exist_ok=True)
    base = (
        f"https://github.com/{catalog['repository']}/releases/download/"
        f"{entry['tag']}"
    )
    names = [*entry["parts"], "build-manifest.json"]
    download(f"{base}/SHA256SUMS", cache / "SHA256SUMS")
    checksums = parse_checksums(cache / "SHA256SUMS", names)
    download(f"{base}/build-manifest.json", cache / "build-manifest.json", checksums["build-manifest.json"])
    if args.manifest_only:
        args.stage.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(cache / "build-manifest.json", args.stage / "build-manifest.json")
        return
    for name in entry["parts"]:
        download(f"{base}/{name}", cache / name, checksums[name])
    parts = [cache / name for name in entry["parts"]]
    if sum(part.stat().st_size for part in parts) != entry["archive_bytes"]:
        raise ValueError("Archive size does not match catalog")
    extract(parts, args.stage)
    try:
        if digest(args.stage / "build-manifest.json") != checksums["build-manifest.json"]:
            raise ValueError("Extracted manifest differs from release manifest")
        for name in (
            "maps/vector/openroadcode.mbtiles",
            "maps/search/openroadcode-search.sqlite",
            "valhalla/valhalla.json",
        ):
            path = args.stage / name
            if not path.is_file() or not path.stat().st_size:
                raise ValueError(f"Missing dataset artifact: {name}")
    except BaseException:
        shutil.rmtree(args.stage)
        raise
    print(f"Verified dataset staged at {args.stage}")


if __name__ == "__main__":
    main()
