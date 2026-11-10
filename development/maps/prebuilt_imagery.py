"""Download a bounded, checksum-checked imagery artifact with byte-range resume."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from tempfile import TemporaryDirectory
import urllib.parse
import urllib.request
import zipfile

from apps.launchers.local_imagery_pack import LocalImageryPack
from tools.map_builder.builder.imagery_artifact import MAX_ARCHIVE_BYTES


def read_descriptor(url, coverage):
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('Pack descriptor must use HTTPS')
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError('Pack descriptor exceeds 64 KiB')
    descriptor = validate_descriptor(raw, coverage)
    return descriptor, urllib.parse.urljoin(url, descriptor['archive'])


def validate_descriptor(raw, coverage):
    descriptor = json.loads(raw)
    name = descriptor.get('archive', '')
    if (descriptor.get('schema') != 1 or descriptor.get('coverage') != coverage
            or not re.fullmatch(r'[a-zA-Z0-9_-]+\.zip', name)
            or type(descriptor.get('bytes')) is not int
            or not 0 < descriptor['bytes'] <= MAX_ARCHIVE_BYTES
            or not re.fullmatch(r'[a-f0-9]{64}', descriptor.get('sha256', ''))):
        raise ValueError('Invalid imagery artifact descriptor or coverage')
    return descriptor


def read_local_archive(path, coverage):
    archive = Path(path).resolve()
    with archive.with_suffix(archive.suffix+'.json').open('rb') as source:
        raw = source.read(65537)
    if len(raw) > 65536:
        raise ValueError('Pack descriptor exceeds 64 KiB')
    descriptor = validate_descriptor(raw, coverage)
    if descriptor['archive'] != archive.name:
        raise ValueError('Descriptor names a different local archive')
    verify_archive(archive, descriptor)
    return descriptor, archive


def verify_archive(archive, descriptor):
    if archive.stat().st_size != descriptor['bytes']:
        raise ValueError('Local archive size differs from its descriptor')
    with archive.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != descriptor['sha256']:
        raise ValueError('Local archive checksum mismatch; active imagery unchanged')


def fetch_archive(url, descriptor, cache):
    cache.mkdir(parents=True, exist_ok=True)
    partial = cache/(descriptor['sha256']+'.zip.part')
    size = descriptor['bytes']
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > size:
        partial.unlink()
        offset = 0
    if offset < size:
        request = urllib.request.Request(url, headers={'Range':f'bytes={offset}-'} if offset else {})
        with urllib.request.urlopen(request, timeout=60) as response:
            if urllib.parse.urlsplit(response.geturl()).scheme != 'https':
                raise ValueError('Artifact download redirected away from HTTPS')
            if response.status == 206:
                expected = f'bytes {offset}-{size-1}/{size}'
                if response.headers.get('Content-Range') != expected:
                    raise ValueError('Artifact server returned an unexpected byte range')
            elif response.status == 200:
                offset = 0  # Server does not support resume: restart safely.
            else:
                raise ValueError('Unexpected artifact response status')
            with partial.open('ab' if offset else 'wb') as target:
                print(f'Download: {offset/1048576:.2f}/{size/1048576:.2f} MiB · {offset*100/size:.0f}%', flush=True)
                while chunk := response.read(min(65536, size-offset+1)):
                    if offset+len(chunk) > size:
                        raise ValueError('Artifact exceeds its declared size')
                    target.write(chunk)
                    offset += len(chunk)
                    print(f'\rDownload: {offset/1048576:.2f}/{size/1048576:.2f} MiB · {offset*100/size:.0f}%', end='', flush=True)
                print(flush=True)
    if partial.stat().st_size != size:
        raise ValueError('Artifact transfer incomplete; rerun to resume')
    with partial.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest != descriptor['sha256']:
        partial.unlink()
        raise ValueError('Artifact checksum mismatch; active imagery unchanged')
    return partial


def unpack(archive, destination, bounds):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix='.imagery-unpack-') as temporary:
        root = Path(temporary)/'pack'
        root.mkdir()
        with zipfile.ZipFile(archive) as source:
            members = source.infolist()
            if len(members) > 2048 or sum(item.file_size for item in members) > MAX_ARCHIVE_BYTES:
                raise ValueError('Imagery archive exceeds extraction limits')
            names = set()
            for item in members:
                path = PurePosixPath(item.filename)
                if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                        or not path.parts or item.filename in names
                        or (item.external_attr >> 16) & 0o170000 == 0o120000):
                    raise ValueError('Unsafe imagery archive entry')
                names.add(item.filename)
                target = root.joinpath(*path.parts)
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open(item) as incoming, target.open('xb') as outgoing:
                        while chunk := incoming.read(65536):
                            outgoing.write(chunk)
        LocalImageryPack.load(root)
        manifest = json.loads((root/'manifest.json').read_text())
        if manifest['bounds_deg'] != list(bounds):
            raise ValueError('Artifact bounds do not match the selected region')
        root.rename(destination)
