"""Transient source failures retry in the same worker; invalid data stays fatal."""
from http.client import IncompleteRead
from io import BytesIO
from unittest.mock import Mock
from urllib.error import HTTPError

import pytest

from development.maps import download_detroit_imagery as policy
from development.maps import static_tile_trial as source


@pytest.fixture(autouse=True)
def no_real_backoff(monkeypatch):
    monkeypatch.setattr(policy, 'wait_to_retry', Mock())


def test_504_recovers_in_same_request(monkeypatch):
    error = HTTPError('https://example.org', 504, 'timeout', {}, None)
    open_mock = Mock(side_effect=[error, BytesIO(b'{"ok":true}')])
    monkeypatch.setattr(source, 'urlopen', open_mock)
    assert source.get_json('https://example.org') == {'ok': True}
    assert open_mock.call_count == 2
    policy.wait_to_retry.assert_called_once()


def test_incomplete_read_retries_entire_response(monkeypatch):
    class Broken(BytesIO):
        def read(self, *args):
            raise IncompleteRead(b'partial', 20)
    first = Broken()
    open_mock = Mock(side_effect=[first, BytesIO(b'complete')])
    monkeypatch.setattr(source, 'urlopen', open_mock)
    assert source.read_source_metadata('https://example.org', limit=20) == b'complete'
    assert first.closed


def test_persistent_timeout_stops_after_six_attempts(monkeypatch):
    open_mock = Mock(side_effect=TimeoutError('temporarily unavailable'))
    monkeypatch.setattr(source, 'urlopen', open_mock)
    with pytest.raises(TimeoutError):
        source.read_source_metadata('https://example.org', limit=20)
    assert open_mock.call_count == 6
    assert policy.wait_to_retry.call_count == 5


def test_missing_file_is_not_retried(monkeypatch):
    open_mock = Mock(side_effect=HTTPError('https://example.org', 404, 'missing', {}, None))
    monkeypatch.setattr(source, 'urlopen', open_mock)
    with pytest.raises(HTTPError):
        source.read_source_metadata('https://example.org', limit=20)
    assert open_mock.call_count == 1
    policy.wait_to_retry.assert_not_called()


def test_oversized_response_is_not_retried(monkeypatch):
    open_mock = Mock(return_value=BytesIO(b'too much'))
    monkeypatch.setattr(source, 'urlopen', open_mock)
    with pytest.raises(ValueError, match='bounded'):
        source.read_source_metadata('https://example.org', limit=2)
    assert open_mock.call_count == 1


def test_staged_directory_lookup_uses_same_retry(monkeypatch):
    error = HTTPError('https://example.org', 504, 'timeout', {}, None)
    listing = b'<ListBucketResult><IsTruncated>false</IsTruncated><Contents><Key>StagedProducts/NAIP/mi_2022/12345/m_1234567_ne_16_060_20220101.tif</Key></Contents></ListBucketResult>'
    open_mock = Mock(side_effect=[error, BytesIO(listing)])
    monkeypatch.setattr(source, 'urlopen', open_mock)
    result = source.staged_imagery_url({'download_url': 'https://earthexplorer.usgs.gov/example',
                                      'Name': 'm_1234567_ne_16_060_20220101', 'Year': 2022})
    assert result.endswith('.tif')
    assert open_mock.call_count == 2
