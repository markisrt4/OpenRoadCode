"""Prebuilt imagery checksums, safe extraction, and HTTP range resume."""

import hashlib
import io
import json
from unittest.mock import Mock, patch
import zipfile

import pytest

from apps.launchers.local_imagery_pack import LocalImageryPack
from apps.launchers.unit_test.test_region_install import write_pack
from development.maps import install_region, prebuilt_imagery
from tools.map_builder.builder.imagery_artifact import package


def test_packaging_and_prebuilt_install_never_contact_usgs(tmp_path):
    bounds = install_region.COVERAGES['metro-detroit'][1]
    root = tmp_path/'built'
    write_pack(root, title='Metro', bounds=bounds)
    archive = tmp_path/'metro.zip'
    descriptor = package(root, archive, 'metro-detroit')
    assert descriptor['bytes'] == archive.stat().st_size
    assert descriptor['sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
    active = tmp_path/'active'
    with (patch.object(install_region, 'imagery_directory', return_value=active),
          patch.object(install_region, 'fetch_archive', return_value=archive),
          patch.object(install_region, 'download_overview') as source):
        install_region.install('metro-detroit', artifact=(descriptor, 'https://host/metro.zip'))
        source.assert_not_called()
    assert LocalImageryPack.load(active).state.title == 'Metro'


def test_archive_resume_requests_remaining_bytes_and_checks_checksum(tmp_path, monkeypatch):
    content = b'a validated archive'
    descriptor = {'bytes':len(content), 'sha256':hashlib.sha256(content).hexdigest()}
    partial = tmp_path/(descriptor['sha256']+'.zip.part')
    partial.write_bytes(content[:5])
    response = io.BytesIO(content[5:])
    response.status = 206
    response.geturl = lambda: 'https://host/pack.zip'
    response.headers = {'Content-Range':f'bytes 5-{len(content)-1}/{len(content)}'}
    opened = Mock(return_value=response)
    monkeypatch.setattr(prebuilt_imagery.urllib.request, 'urlopen', opened)
    assert prebuilt_imagery.fetch_archive('https://host/pack.zip', descriptor, tmp_path).read_bytes() == content
    assert opened.call_args.args[0].get_header('Range') == 'bytes=5-'


def test_corrupt_archive_cannot_replace_active_pack(tmp_path):
    bounds = install_region.COVERAGES['metro-detroit'][1]
    original = tmp_path/'original'
    write_pack(original, title='Old', bounds=bounds)
    active = tmp_path/'active'
    active.symlink_to(original)
    archive = tmp_path/'broken.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        manifest = json.loads((original/'manifest.json').read_text())
        zipped.writestr('manifest.json', json.dumps(manifest))
        zipped.writestr('imagery.jpg', b'corrupted')
    with (patch.object(install_region, 'imagery_directory', return_value=active),
          patch.object(install_region, 'fetch_archive', return_value=archive)):
        with pytest.raises(ValueError, match='checksum'):
            install_region.install('metro-detroit', update=True, artifact=({}, 'https://host/pack.zip'))
    assert active.resolve() == original


def test_archive_path_traversal_is_rejected(tmp_path):
    archive = tmp_path/'unsafe.zip'
    with zipfile.ZipFile(archive, 'w') as zipped:
        zipped.writestr('../escape', b'bad')
    with pytest.raises(ValueError, match='Unsafe'):
        prebuilt_imagery.unpack(archive, tmp_path/'pack', (-84,42,-82,44))
    assert not (tmp_path/'escape').exists()


def test_descriptor_rejects_wrong_region_before_download(monkeypatch):
    response = io.BytesIO(json.dumps({'schema':1, 'coverage':'another-region', 'archive':'pack.zip',
                                    'bytes':10, 'sha256':'a'*64}).encode())
    monkeypatch.setattr(prebuilt_imagery.urllib.request, 'urlopen', Mock(return_value=response))
    with pytest.raises(ValueError, match='coverage'):
        prebuilt_imagery.read_descriptor('https://host/pack.zip.json', 'metro-detroit')
