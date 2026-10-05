from pathlib import Path
from unittest.mock import patch

from common.navigation_data import search_database_path
from controllers.poi.poi_search_controller import PoiSearchController
from tools.poi_download import default_database


def test_termux_runtime_opens_the_same_index_as_downloader(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENROADCODE_DATA_ROOT', raising=False)
    monkeypatch.delenv('XDG_DATA_HOME', raising=False)
    monkeypatch.setenv('PREFIX', '/data/data/com.termux/files/usr')
    with patch('common.navigation_data.Path.home', return_value=tmp_path), \
         patch('controllers.poi.poi_search_controller.SqlitePoiSearchSource') as source:
        controller = PoiSearchController(source=object())
        controller._offline_source()
        source.assert_called_once_with(default_database())
        assert default_database() == tmp_path / '.local/share/openroadcode/maps/search/openroadcode-search.sqlite'


def test_data_root_override_is_resolved_when_runtime_opens_index(tmp_path, monkeypatch):
    monkeypatch.setenv('OPENROADCODE_DATA_ROOT', str(tmp_path))
    assert search_database_path() == tmp_path / 'maps/search/openroadcode-search.sqlite'


def test_linux_installed_index_uses_srv(monkeypatch):
    monkeypatch.delenv('OPENROADCODE_DATA_ROOT', raising=False)
    monkeypatch.delenv('PREFIX', raising=False)
    with patch('common.navigation_data.Path.is_file', return_value=True):
        assert search_database_path() == Path('/srv/openroadcode/maps/search/openroadcode-search.sqlite')
