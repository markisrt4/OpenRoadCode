# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""NOAA index selection, bounded downloads, numeric coloring, and cache separation."""

from io import BytesIO
import json
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlparse

from PIL import Image
import pytest
import requests

from controllers.weather.hrrr_tiles import HrrrTileSource, color_hrrr_reflectivity, tile_bounds
from controllers.weather.providers.hrrr_radar_provider import HrrrRadarProvider, reflectivity_range
from controllers.weather.radar_tile_service import _UNIVERSAL_DBZ
from controllers.weather import RadarFrame, RadarPalette, RadarTileService, WeatherRadarController
from controllers.weather.environmental_radar_injection_controller import EnvironmentalRadarInjectionController


NOW = 1790945700  # 2026-10-02 12:55 UTC
HOUR = NOW // 3600 * 3600
RUN = "2026100212"


@pytest.fixture(autouse=True)
def native_dependency_checked_separately():
    with patch("controllers.weather.providers.hrrr_radar_provider.check_gdal_tools"):
        yield


def _index(run=RUN):
    return f"1:0:d={run}:REFC:entire atmosphere:1 hour fcst:\n2:500:d={run}:TMP:2 m above ground:1 hour fcst:\n"


def _response(index=None, status=200):
    response = Mock(status_code=status, text=_index() if index is None else index)
    return response


def _provider():
    session = Mock()
    session.get.return_value = _response()
    return HrrrRadarProvider(session=session, clock=lambda: NOW), session


def test_index_selects_only_reflectivity_and_not_the_whole_grib():
    assert reflectivity_range(_index(), RUN) == (0, 499)
    assert reflectivity_range(f"1:700:d={RUN}:REFC:entire atmosphere:1 hour fcst:\n", RUN) == (700, None)


@pytest.mark.parametrize("index", [
    f"1:0:d={RUN}:TMP:2 m above ground:1 hour fcst:\n",
    _index("2026100211"),
    f"1:500:d={RUN}:REFC:entire atmosphere:1 hour fcst:\n2:400:d={RUN}:TMP:surface:1 hour fcst:\n",
])
def test_wrong_field_run_or_offsets_are_rejected(index):
    with pytest.raises(ValueError):
        reflectivity_range(index, RUN)


def test_provider_returns_six_future_hours_from_one_run():
    provider, session = _provider()
    frames = provider.get_frames()
    assert [frame.timestamp for frame in frames] == [HOUR + step * 3600 for step in range(1, 7)]
    assert session.get.call_count == 6
    assert session.get.call_args.args[0].endswith("/hrrr.t12z.wrfsfcf06.grib2.idx")
    assert all(frame.tile_url.startswith(f"orc-hrrr://{RUN}/") for frame in frames)
    assert parse_qs(urlparse(frames[0].tile_url).query)["end"] == ["499"]


def test_partial_latest_run_falls_back_as_a_whole():
    provider, session = _provider()
    session.get.side_effect = [
        _response(), _response(status=404),
        *[_response(_index("2026100211")) for _ in range(6)],
    ]
    frames = provider.get_frames()
    assert all(frame.tile_url.startswith("orc-hrrr://2026100211/") for frame in frames)
    assert "/f02/" in frames[0].tile_url
    assert "/f07/" in frames[-1].tile_url


def test_no_model_data_is_reported_without_inventing_frames():
    provider, session = _provider()
    session.get.return_value = _response(status=404)
    with pytest.raises(RuntimeError, match="no complete recent run"):
        provider.get_frames()
    assert session.get.call_count == 5


def test_network_failure_is_not_treated_as_no_precipitation():
    provider, session = _provider()
    session.get.return_value.raise_for_status.side_effect = requests.HTTPError("403")
    with pytest.raises(requests.HTTPError):
        provider.get_frames()


def test_forecast_opens_at_nearest_future_not_six_hour_edge():
    provider, _ = _provider()
    controller = WeatherRadarController(provider, Mock())
    assert controller.show_latest().timestamp == HOUR + 3600
    assert controller.is_forecast


def test_web_mercator_bounds():
    assert tile_bounds(1, 0, 0) == pytest.approx([-20037508.342789244, 0, 0, 20037508.342789244])
    with pytest.raises(ValueError):
        tile_bounds(4, 16, 1)


def _grib_message():
    data = bytearray(24)
    data[:4] = b"GRIB"
    data[7] = 2
    data[8:16] = len(data).to_bytes(8, "big")
    data[-4:] = b"7777"
    return bytes(data)


def _range_response(data=None, status=206, content_range="bytes 100-123/10000"):
    data = _grib_message() if data is None else data
    response = Mock(status_code=status, headers={"Content-Range": content_range})
    response.iter_content.return_value = iter([data])
    return response


def test_download_requires_a_valid_single_message_byte_range(tmp_path):
    session = Mock()
    session.get.return_value = _range_response()
    source = HrrrTileSource(tmp_path, session)
    assert source._download("https://example.test/field.grib2", 100, 123) == _grib_message()
    assert session.get.call_args.kwargs["headers"]["Range"] == "bytes=100-123"
    assert session.get.call_args.kwargs["stream"] is True


@pytest.mark.parametrize(("status", "content_range", "data"), [
    (200, "", _grib_message()),
    (206, "bytes 0-23/10000", _grib_message()),
    (206, "bytes 100-123/10000", b"truncated"),
])
def test_full_file_wrong_range_and_truncated_download_are_rejected(tmp_path, status, content_range, data):
    session = Mock()
    session.get.return_value = _range_response(data, status, content_range)
    with pytest.raises(RuntimeError):
        HrrrTileSource(tmp_path, session)._download("https://example.test/field.grib2", 100, 123)
    session.get.return_value.close.assert_called_once()


@pytest.mark.parametrize("attributes", [
    {"GRIB_ELEMENT": "TMP", "GRIB_SHORT_NAME": "0-EATM", "GRIB_VALID_TIME": str(HOUR + 3600)},
    {"GRIB_ELEMENT": "REFC", "GRIB_SHORT_NAME": "0-SFC", "GRIB_VALID_TIME": str(HOUR + 3600)},
    {"GRIB_ELEMENT": "REFC", "GRIB_SHORT_NAME": "0-EATM", "GRIB_VALID_TIME": str(HOUR + 7200)},
])
def test_decoder_rejects_wrong_variable_surface_or_valid_time(tmp_path, attributes):
    provider, _ = _provider()
    source = HrrrTileSource(tmp_path, Mock())
    source._checked = True
    source._download = Mock(return_value=_grib_message())
    source._run = Mock(return_value=json.dumps({"bands": [{"metadata": {"": attributes}}]}))
    with pytest.raises(RuntimeError, match="not composite reflectivity"):
        source.tile(provider.get_frames()[0].tile_url, 4, 3, 6)
    source._run.assert_called_once()


def _tiff():
    image = Image.new("F", (256, 256), -9999)
    image.putpixel((0, 0), 20)
    image.putpixel((1, 0), 50)
    image.putpixel((2, 0), float("nan"))
    stream = BytesIO()
    image.save(stream, format="TIFF")
    return stream.getvalue()


def test_raw_reflectivity_becomes_transparent_clear_and_colored_precipitation():
    result = Image.open(BytesIO(color_hrrr_reflectivity(_tiff(), _UNIVERSAL_DBZ)))
    assert result.getpixel((0, 0)) == (0, 163, 224, 255)
    assert result.getpixel((1, 0)) == (193, 0, 0, 255)
    assert result.getpixel((2, 0))[3] == 0
    assert result.getpixel((3, 0))[3] == 0


def test_colorized_output_is_not_misread_as_dbz():
    stream = BytesIO()
    Image.new("RGB", (256, 256)).save(stream, format="TIFF")
    with pytest.raises(ValueError, match="raw single-band"):
        color_hrrr_reflectivity(stream.getvalue(), _UNIVERSAL_DBZ)


def test_same_timestamp_from_different_sources_has_separate_tiles(tmp_path):
    service = RadarTileService(cache_root=tmp_path)
    try:
        observed = service.tile_url(RadarFrame(100, "https://observed.test/{z}/{x}/{y}.png"), RadarPalette.UNIVERSAL)
        forecast = service.tile_url(RadarFrame(100, "https://forecast.test/{z}/{x}/{y}.png"), RadarPalette.UNIVERSAL)
        assert observed != forecast
    finally:
        service.close()


def test_hrrr_tiles_flow_through_local_cache_and_classic_palette(tmp_path):
    provider, _ = _provider()
    service = RadarTileService(cache_root=tmp_path)
    service._hrrr_tiles.tile = Mock(return_value=_tiff())
    try:
        path = urlparse(service.tile_url(provider.get_frames()[0], RadarPalette.UNIVERSAL)).path.format(z=4, x=3, y=6)
        universal = service._handle_path(path)
        classic = service._handle_path(path.replace("/universal/", "/classic/"))
        assert Image.open(BytesIO(universal)).getpixel((0, 0)) == (0, 163, 224, 255)
        assert Image.open(BytesIO(classic)).getpixel((0, 0)) == (0, 200, 0, 255)
        service._hrrr_tiles.tile.assert_called_once()
    finally:
        service.close()


def test_environmental_injection_restores_selected_forecast_source():
    provider, _ = _provider()
    radar = WeatherRadarController(provider, Mock())
    bridge = Mock()
    bridge.read_environmental_injection.side_effect = ["STORM", "OFF"]
    injection = EnvironmentalRadarInjectionController(radar, bridge)
    injection.set_live_provider(provider)
    injection.refresh()
    assert not radar.is_forecast
    injection.refresh()
    assert radar.is_forecast
