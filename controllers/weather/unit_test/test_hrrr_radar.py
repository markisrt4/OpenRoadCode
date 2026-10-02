# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""NOAA metadata, forecast selection, and numeric reflectivity tile conversion."""

from io import BytesIO
import json
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

from PIL import Image
import pytest

from controllers.weather.hrrr_tiles import color_hrrr_reflectivity, hrrr_export_url
from controllers.weather.providers.hrrr_radar_provider import HrrrRadarProvider
from controllers.weather.radar_tile_service import _UNIVERSAL_DBZ
from controllers.weather import RadarFrame, RadarPalette, RadarTileService, WeatherRadarController
from controllers.weather.environmental_radar_injection_controller import EnvironmentalRadarInjectionController


SERVICE = "https://example.test/reflectivity/HRRR_Composite_Reflectivity/ImageServer"


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    return response


def _provider(features):
    session = Mock()
    session.get.side_effect = [
        _response({"services": [{"name": "reflectivity/HRRR_Composite_Reflectivity", "type": "ImageServer"}]}),
        _response({"timeInfo": {"startTimeField": "StdTime"}, "objectIdField": "OBJECTID"}),
        _response({"features": [{"attributes": {"StdTime": time, "OBJECTID": oid}} for time, oid in features]}),
    ]
    provider = HrrrRadarProvider(session=session, clock=lambda: 10000)
    return provider, session


def test_forecast_discovery_filters_past_and_deduplicates_valid_times():
    provider, session = _provider([(9000_000, 1), (11000_000, 2), (11000_000, 3), (12000_000, 4), (40000_000, 5)])
    frames = provider.get_frames()
    assert [frame.timestamp for frame in frames] == [11000, 12000]
    assert frames[0].tile_url.startswith("orc-hrrr://3/")
    assert all(frame.max_zoom == 9 for frame in frames)
    assert "TIMESTAMP" in session.get.call_args.kwargs["params"]["where"]


def test_no_future_data_is_reported_without_inventing_frames():
    provider, _ = _provider([(9000_000, 1)])
    with pytest.raises(RuntimeError, match="no upcoming forecast"):
        provider.get_frames()


def test_arcgis_error_is_not_treated_as_empty_weather():
    session = Mock()
    session.get.return_value = _response({"error": {"message": "service unavailable"}})
    with pytest.raises(RuntimeError, match="service unavailable"):
        HrrrRadarProvider(session=session).get_frames()


def test_forecast_opens_at_nearest_future_not_six_hour_edge():
    provider, _ = _provider([(11000_000, 2), (12000_000, 3)])
    controller = WeatherRadarController(provider, Mock())
    assert controller.show_latest().timestamp == 11000
    assert controller.is_forecast


def test_export_locks_raster_and_projects_correct_web_mercator_bounds():
    url = hrrr_export_url("orc-hrrr://42/1/0/0.tiff?service=" + SERVICE, 1, 0, 0)
    params = parse_qs(urlparse(url).query)
    assert params["bboxSR"] == ["3857"]
    assert params["imageSR"] == ["3857"]
    assert params["format"] == ["tiff"]
    assert json.loads(params["mosaicRule"][0])["lockRasterIds"] == [42]
    assert [float(value) for value in params["bbox"][0].split(",")] == pytest.approx([-20037508.342789244, 0, 0, 20037508.342789244])


def test_raw_reflectivity_becomes_transparent_clear_and_colored_precipitation():
    image = Image.new("F", (256, 256), -9999)
    image.putpixel((0, 0), 20)
    image.putpixel((1, 0), 50)
    image.putpixel((2, 0), float("nan"))
    stream = BytesIO()
    image.save(stream, format="TIFF")
    result = Image.open(BytesIO(color_hrrr_reflectivity(stream.getvalue(), _UNIVERSAL_DBZ)))
    assert result.getpixel((0, 0)) == (0, 163, 224, 255)
    assert result.getpixel((1, 0)) == (193, 0, 0, 255)
    assert result.getpixel((2, 0))[3] == 0
    assert result.getpixel((3, 0))[3] == 0


def test_colorized_server_output_is_rejected_instead_of_misreading_rgb_as_dbz():
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
        assert len(service._frames) == 2
    finally:
        service.close()


def test_hrrr_numeric_tiles_flow_through_local_cache_and_classic_palette(tmp_path):
    image = Image.new("F", (256, 256), 20)
    stream = BytesIO()
    image.save(stream, format="TIFF")
    session = Mock()
    session.get.return_value.content = stream.getvalue()
    service = RadarTileService(cache_root=tmp_path, session=session)
    try:
        frame = RadarFrame(123, "orc-hrrr://42/{z}/{x}/{y}.tiff?service=" + SERVICE)
        path = urlparse(service.tile_url(frame, RadarPalette.UNIVERSAL)).path.format(z=4, x=3, y=6)
        universal = service._handle_path(path)
        classic = service._handle_path(path.replace("/universal/", "/classic/"))
        assert Image.open(BytesIO(universal)).getpixel((0, 0)) == (0, 163, 224, 255)
        assert Image.open(BytesIO(classic)).getpixel((0, 0)) == (0, 200, 0, 255)
        session.get.assert_called_once()
    finally:
        service.close()


def test_environmental_injection_restores_selected_forecast_source():
    provider, _ = _provider([(11000_000, 2)])
    radar = WeatherRadarController(provider, Mock())
    bridge = Mock()
    bridge.read_environmental_injection.side_effect = ["STORM", "OFF"]
    injection = EnvironmentalRadarInjectionController(radar, bridge)
    injection.set_live_provider(provider)
    injection.refresh()
    assert not radar.is_forecast
    injection.refresh()
    assert radar.is_forecast
