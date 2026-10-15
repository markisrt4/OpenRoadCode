# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Distinguish missing raster support from a broken native GDAL installation."""
import subprocess
from unittest.mock import Mock, patch

import pytest

from controllers.weather.hrrr_tiles import check_gdal_tools


@patch('controllers.weather.gdal_tools.shutil.which', return_value='/termux/bin/tool')
def test_available_grib_driver_passes(_which):
    result = Mock(returncode=0, stdout='  GRIB -raster- (rwv): GRIdded Binary\n', stderr='')
    with patch('controllers.weather.hrrr_tiles.subprocess.run', return_value=result):
        check_gdal_tools()


@patch('controllers.weather.gdal_tools.shutil.which', return_value='/termux/bin/tool')
def test_linker_failure_reports_missing_library_instead_of_missing_decoder(_which):
    result = Mock(returncode=1, stdout='', stderr='CANNOT LINK EXECUTABLE: libOpenEXR-3_4.so not found')
    with patch('controllers.weather.hrrr_tiles.subprocess.run', return_value=result):
        with pytest.raises(RuntimeError, match='GDAL cannot run.*libOpenEXR-3_4.so') as failure:
            check_gdal_tools()
    assert 'GRIB decoder' not in str(failure.value)


@patch('controllers.weather.gdal_tools.shutil.which', return_value='/termux/bin/tool')
def test_running_gdal_without_grib_reports_missing_decoder(_which):
    result = Mock(returncode=0, stdout='GTiff -raster- (rwv): GeoTIFF\n', stderr='')
    with patch('controllers.weather.hrrr_tiles.subprocess.run', return_value=result):
        with pytest.raises(RuntimeError, match='GRIB decoder'):
            check_gdal_tools()


@pytest.mark.parametrize('error', [OSError('loader failure'), subprocess.TimeoutExpired('gdalinfo', 20)])
@patch('controllers.weather.gdal_tools.shutil.which', return_value='/termux/bin/tool')
def test_failed_probe_is_reported_without_claiming_missing_grib(_which, error):
    with patch('controllers.weather.hrrr_tiles.subprocess.run', side_effect=error):
        with pytest.raises(RuntimeError, match='capability check could not run'):
            check_gdal_tools()
