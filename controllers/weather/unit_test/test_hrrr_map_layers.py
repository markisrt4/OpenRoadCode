# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Field selection and heatmap correctness for full-area model layers."""

from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock
from urllib.parse import parse_qs, urlparse

from PIL import Image
import pytest

from controllers.weather.hrrr_map_layers import (
    HrrrMapLayerProvider, field_range, color_model_layer, TEMPERATURE_COLORS, WIND_COLORS,
)


RUN = '2026100212'
HOUR = int(datetime(2026, 10, 2, 12, tzinfo=timezone.utc).timestamp())
INDEX = '\n'.join((f'1:0:d={RUN}:TMP:2 m above ground:1 hour fcst:',
                   f'2:100:d={RUN}:UGRD:10 m above ground:1 hour fcst:',
                   f'3:200:d={RUN}:VGRD:10 m above ground:1 hour fcst:',
                   f'4:300:d={RUN}:TMP:surface:1 hour fcst:'))


def tiff(value):
    image = Image.new('F', (256, 256), value)
    output = BytesIO()
    image.save(output, format='TIFF')
    return output.getvalue()


@pytest.mark.parametrize('kind,element', [('temperature', 'TMP'), ('wind', 'UGRD')])
def test_provider_picks_exact_surface_height_and_matching_run(kind, element, monkeypatch):
    monkeypatch.setattr('controllers.weather.hrrr_map_layers.check_gdal_tools', lambda: None)
    session = Mock()
    session.get.return_value.status_code = 200
    session.get.return_value.text = INDEX
    frame = HrrrMapLayerProvider(session, clock=lambda: HOUR).get_frame(kind)
    assert frame.timestamp == HOUR + 3600
    params = parse_qs(urlparse(frame.tile_url).query)
    assert params['element'] == [element]
    assert params['kind'] == [kind]
    if kind == 'wind':
        second = parse_qs(urlparse(params['secondary'][0]).query)
        assert second['element'] == ['VGRD']
        assert second['start'] == ['200']
        assert second['end'] == ['299']


def test_field_range_rejects_wrong_height_and_duplicate_matches():
    with pytest.raises(ValueError):
        field_range(INDEX, RUN, 'TMP', '10 m above ground')
    with pytest.raises(ValueError):
        field_range(INDEX + f'\n5:400:d={RUN}:TMP:2 m above ground:1 hour fcst:', RUN, 'TMP', '2 m above ground')


def test_temperature_palette_uses_celsius_and_wind_uses_both_components():
    with Image.open(BytesIO(color_model_layer(tiff(20), 'temperature'))) as image:
        assert image.getpixel((0, 0)) == (*TEMPERATURE_COLORS[4][1], 255)
    with Image.open(BytesIO(color_model_layer(tiff(3), 'wind', tiff(4)))) as image:
        assert image.getpixel((0, 0)) == (*WIND_COLORS[1][1], 255)


@pytest.mark.parametrize('kind,raw,second', [('temperature', -9999, None), ('temperature', float('nan'), None),
                                           ('wind', 3, -9999), ('wind', float('inf'), 4)])
def test_missing_or_invalid_data_stays_transparent(kind, raw, second):
    data = color_model_layer(tiff(raw), kind, tiff(second) if second is not None else None)
    with Image.open(BytesIO(data)) as image:
        assert image.getchannel('A').getextrema() == (0, 0)


def test_wind_without_both_components_is_rejected():
    with pytest.raises(ValueError):
        color_model_layer(tiff(3), 'wind')


def test_missing_current_run_falls_back_without_changing_forecast_time(monkeypatch):
    monkeypatch.setattr('controllers.weather.hrrr_map_layers.check_gdal_tools', lambda: None)
    session = Mock()
    missing = Mock(status_code=404)
    ready = Mock(status_code=200, text=INDEX.replace(RUN, '2026100211'))
    session.get.side_effect = [missing, ready]
    frame = HrrrMapLayerProvider(session, clock=lambda: HOUR).get_frame('temperature')
    assert frame.timestamp == HOUR + 3600
    assert '2026100211/f02' in frame.tile_url
