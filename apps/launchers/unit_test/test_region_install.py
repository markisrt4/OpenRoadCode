"""Regional update failures must preserve usable installed imagery."""
import hashlib
import json
from unittest.mock import patch

import pytest

from development.maps import install_region
from apps.launchers.local_imagery_pack import LocalImageryPack


def write_pack(destination, **kwargs):
    destination.mkdir()
    content = b'\xff\xd8fixture'
    (destination/'imagery.jpg').write_bytes(content)
    (destination/'manifest.json').write_text(json.dumps({
        'schema': 1, 'image': 'imagery.jpg', 'sha256': hashlib.sha256(content).hexdigest(),
        'title': kwargs['title'], 'attribution': 'USGS fixture', 'bounds_deg': kwargs['bounds'],
    }))


def test_failed_update_keeps_active_revision(tmp_path):
    active = tmp_path/'active'
    with patch.object(install_region, 'imagery_directory', return_value=active):
        with patch.object(install_region, 'download', side_effect=write_pack):
            install_region.install('metro-detroit')
        original = active.resolve()
        with patch.object(install_region, 'download', side_effect=RuntimeError('offline')):
            with pytest.raises(RuntimeError, match='offline'):
                install_region.install('metro-detroit', update=True)
        assert active.resolve() == original
        assert LocalImageryPack.load(active).state.title == 'Metro Detroit overview'
        with patch.object(install_region, 'download', side_effect=write_pack):
            install_region.install('metro-detroit', update=True)
        assert active.resolve() != original
        assert original.exists()


def test_declining_plan_does_not_download(monkeypatch):
    monkeypatch.setattr('sys.argv', ['install_region', '--coverage', 'metro-detroit'])
    monkeypatch.setattr('builtins.input', lambda _: 'n')
    with patch.object(install_region, 'install') as install:
        assert install_region.main() == 0
        install.assert_not_called()


def test_viewer_prefers_detail_and_uses_overview_outside_detail(tmp_path, monkeypatch):
    import math
    from apps.launchers import local_imagery_pack
    from ui.navigation import GeoPoint

    monkeypatch.setattr(local_imagery_pack, 'openroadcode_data_dir', lambda *parts: tmp_path/parts[-1])
    overview = tmp_path/'metro-detroit-imagery-active'
    detail = tmp_path/'detroit-midtown-imagery-active'
    write_pack(overview, title='Overview', bounds=install_region.COVERAGES['metro-detroit'][1])
    write_pack(detail, title='Detail', bounds=install_region.COVERAGES['detroit-midtown'][1])
    detroit = GeoPoint(math.radians(42.34), math.radians(-83.05))
    suburb = GeoPoint(math.radians(42.7), math.radians(-83.2))
    assert local_imagery_pack.preferred_imagery_directory(detroit) == detail
    assert local_imagery_pack.preferred_imagery_directory(suburb) == overview
