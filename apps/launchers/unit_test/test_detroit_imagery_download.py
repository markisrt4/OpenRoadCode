"""Explicit source selection and offline-pack provenance without live downloads."""

import io
import json
from unittest.mock import Mock

import pytest

from development.maps import download_detroit_imagery as downloader
from apps.launchers.local_imagery_pack import LocalImageryPack


@pytest.mark.parametrize("coverage,title", [("detroit-downtown","Detroit"),("pine-knob","Pine Knob")])
def test_export_locks_newest_naip_sources_and_retains_provenance(tmp_path, monkeypatch, coverage, title):
    records = [
        {"attributes":{"OBJECTID":1,"Name":"m_4208307_sw_16_2020","Year":2020}},
        {"attributes":{"OBJECTID":2,"Name":"m_4208307_sw_16_2022","Year":2022}},
        {"attributes":{"OBJECTID":3,"Name":"m_partner","Year":2024}},
    ]
    west,south,east,north = downloader.PRESETS[coverage][1]
    export = {"href":"https://imagery.nationalmap.gov/export/example.jpg", "width":2048,"height":1536,
              "extent":{"xmin":west,"ymin":south,"xmax":east,"ymax":north,"spatialReference":{"wkid":4326}}}
    service = Mock(side_effect=[{"serviceDescription":"public domain imagery"}, {"features":records}, export])
    monkeypatch.setattr(downloader,"get_json",service)
    monkeypatch.setattr(downloader.urllib.request,"urlopen",lambda *args, **kwargs: io.BytesIO(b"\xff\xd8fixture"))
    destination = tmp_path / "pack"
    downloader.download(destination, bounds=(west,south,east,north), title=title)
    rule = json.loads(service.call_args.kwargs["mosaicRule"])
    assert rule["lockRasterIds"] == [2]
    document = json.loads((destination / "manifest.json").read_text())
    assert document["source_records"] == [records[1]["attributes"]]
    assert document["title"] == f"{title} NAIP 2022"
    assert (destination / "source-service.json").exists()
    assert LocalImageryPack.load(destination).state.attribution.startswith("USGS / USDA")


def test_missing_naip_does_not_silently_substitute_partner_imagery(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"get_json",Mock(side_effect=[
        {"serviceDescription":"public domain imagery"},
        {"features":[{"attributes":{"Name":"other","Year":2024}}]},
    ]))
    with pytest.raises(RuntimeError,match="No identifiable"):
        downloader.download(tmp_path / "pack")
    assert not (tmp_path / "pack").exists()


def test_source_rights_change_stops_download(tmp_path, monkeypatch):
    monkeypatch.setattr(downloader,"get_json",Mock(return_value={"serviceDescription":"other imagery"}))
    with pytest.raises(RuntimeError,match="rights"):
        downloader.download(tmp_path / "pack")


def test_pine_imagery_is_selected_only_inside_its_coverage(tmp_path, monkeypatch):
    import math
    from apps.launchers import local_imagery_pack as packs
    from ui.navigation import GeoPoint
    from ui.navigation.local_imagery_state import LocalImageryState
    pine = tmp_path/'pine'
    pine.mkdir()
    (pine/'manifest.json').write_text('{}')
    bounds = downloader.PRESETS['pine-knob'][1]
    state = LocalImageryState('Pine Knob', 'USGS', *(math.radians(v) for v in bounds))
    monkeypatch.setattr(packs, 'pine_knob_imagery_directory', lambda: pine)
    monkeypatch.setattr(packs, 'detroit_pack_directory', lambda: tmp_path/'detroit')
    monkeypatch.setattr(packs.LocalImageryPack, 'load', lambda directory: Mock(state=state))
    assert packs.preferred_imagery_directory(GeoPoint(math.radians(42.75),math.radians(-83.38))) == pine
    assert packs.preferred_imagery_directory(GeoPoint(math.radians(42.33),math.radians(-83.04))) == tmp_path/'detroit'


def test_imagery_retries_server_errors_without_leaving_a_partial_pack(monkeypatch):
    from urllib.error import HTTPError
    call = Mock(side_effect=HTTPError(downloader.SERVICE,500,'Server error',{},None))
    monkeypatch.setattr(downloader.urllib.request, 'urlopen', call)
    monkeypatch.setattr(downloader.time, 'sleep', lambda seconds: None)
    with pytest.raises(HTTPError):
        downloader.open_source(downloader.SERVICE, timeout=60)
    assert call.call_count == 3


def test_catalog_network_failure_identifies_stage_and_endpoint(monkeypatch):
    from urllib.error import HTTPError
    monkeypatch.setattr(downloader, 'open_source', Mock(side_effect=HTTPError(downloader.SERVICE,502,'Bad Gateway',{},None)))
    with pytest.raises(RuntimeError, match='NAIP source catalog failed after retries') as error:
        downloader.get_json('/query', where="State='MI'")
    assert downloader.SERVICE+'/query' in str(error.value)


def test_truncated_catalog_fetches_complete_ids_with_smaller_batches(monkeypatch):
    service = Mock(side_effect=[
        {'features': [], 'exceededTransferLimit': True},
        {'objectIds': [1, 2]},
        {'features': [{'attributes': {'OBJECTID': 1}}], 'exceededTransferLimit': True},
        {'features': [{'attributes': {'OBJECTID': 1, 'Year': 2020}}]},
        {'features': [{'attributes': {'OBJECTID': 2, 'Year': 2022}}]},
    ])
    monkeypatch.setattr(downloader, 'get_json', service)
    catalog = downloader.source_catalog(downloader.BOUNDS)
    assert [f['attributes']['OBJECTID'] for f in catalog['features']] == [1, 2]
    assert service.call_args_list[1].kwargs['returnIdsOnly'] == 'true'
    assert service.call_args_list[2].kwargs['objectIds'] == '1,2'
    assert catalog['source_index']['objectIds'] == [1, 2]


def test_catalog_missing_id_fails_before_export_or_install(tmp_path, monkeypatch):
    service = Mock(side_effect=[
        {'serviceDescription': 'public domain'},
        {'features': [], 'exceededTransferLimit': True},
        {'objectIds': [1, 2]},
        {'features': [{'attributes': {'OBJECTID': 1}}]},
    ])
    monkeypatch.setattr(downloader, 'get_json', service)
    with pytest.raises(RuntimeError, match='batch is incomplete'):
        downloader.download(tmp_path/'pack')
    assert not (tmp_path/'pack').exists()
    assert all(call.args[0] != '/exportImage' for call in service.call_args_list)


def test_image_progress_reports_size_and_percentage(capsys):
    response = io.BytesIO(b'\xff\xd8'+b'x'*131070)
    response.headers = {'Content-Length': '131072'}
    assert len(downloader.read_image(response)) == 131072
    output = capsys.readouterr().out
    assert '0.00 / 0.12 MiB · 0%' in output
    assert '0.12 / 0.12 MiB · 100%' in output


def test_image_progress_does_not_invent_total(capsys):
    assert downloader.read_image(io.BytesIO(b'fixture')) == b'fixture'
    output = capsys.readouterr().out
    assert 'total size unknown · complete' in output
    assert '100%' not in output


def test_truncated_image_never_reports_completion(capsys):
    response = io.BytesIO(b'short')
    response.headers = {'Content-Length': '100'}
    with pytest.raises(RuntimeError, match='Content-Length'):
        downloader.read_image(response)
    assert '100%' not in capsys.readouterr().out


def test_oversized_image_stops_at_payload_cap(monkeypatch):
    monkeypatch.setattr(downloader, 'MAX_BYTES', 8)
    with pytest.raises(RuntimeError, match='20 MiB'):
        downloader.read_image(io.BytesIO(b'0123456789'))


def test_catalog_retries_timeout_during_body_read_and_closes_response(monkeypatch):
    first = Mock()
    first.__enter__ = Mock(return_value=first)
    first.__exit__ = Mock(return_value=False)
    first.read.side_effect = TimeoutError('body read timed out')
    second = io.BytesIO(b'{"features": []}')
    opened = Mock(side_effect=[first, second])
    monkeypatch.setattr(downloader, 'open_source', opened)
    monkeypatch.setattr(downloader.time, 'sleep', lambda _: None)
    assert downloader.get_json('/query', timeout=30, attempts=2) == {'features': []}
    assert opened.call_count == 2
    assert opened.call_args.kwargs == {'timeout': 30, 'attempts': 1}
    first.__exit__.assert_called_once()
    assert second.closed


def test_slow_catalog_batch_is_split_without_losing_records(monkeypatch):
    failure = downloader.SourceRequestError('slow response')
    failure.__cause__ = TimeoutError('timed out')
    query = Mock(side_effect=[
        {'exceededTransferLimit': True}, {'objectIds': [1, 2]}, failure,
        {'features': [{'attributes': {'OBJECTID': 1}}]},
        {'features': [{'attributes': {'OBJECTID': 2}}]},
    ])
    monkeypatch.setattr(downloader, 'get_json', query)
    catalog = downloader.source_catalog(downloader.BOUNDS)
    assert [feature['attributes']['OBJECTID'] for feature in catalog['features']] == [1, 2]
    assert [call.kwargs['objectIds'] for call in query.call_args_list[2:]] == ['1,2', '1', '2']


def test_catalog_batches_are_bounded_and_non_retryable_failure_stops(monkeypatch):
    from urllib.error import HTTPError
    identifiers = list(range(41))

    def query(endpoint, **parameters):
        if parameters.get('returnIdsOnly'):
            return {'objectIds': identifiers}
        if 'objectIds' not in parameters:
            return {'exceededTransferLimit': True}
        ids = list(map(int, parameters['objectIds'].split(',')))
        assert len(ids) <= 20
        return {'features': [{'attributes': {'OBJECTID': value}} for value in ids]}

    monkeypatch.setattr(downloader, 'get_json', query)
    assert len(downloader.source_catalog(downloader.BOUNDS)['features']) == 41
    failure = downloader.SourceRequestError('forbidden')
    failure.__cause__ = HTTPError(downloader.SERVICE, 403, 'forbidden', {}, None)
    calls = Mock(side_effect=[{'exceededTransferLimit': True}, {'objectIds': [1, 2]}, failure])
    monkeypatch.setattr(downloader, 'get_json', calls)
    with pytest.raises(downloader.SourceRequestError, match='forbidden'):
        downloader.source_catalog(downloader.BOUNDS)
    assert calls.call_count == 3
