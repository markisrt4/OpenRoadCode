# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Isolated tool selection and subprocess routing without native GDAL."""
from unittest.mock import Mock

import pytest

from controllers.weather.gdal_tools import TOOLS, gdal_tool
from controllers.weather.hrrr_tiles import HrrrTileSource


@pytest.fixture
def installation(tmp_path, monkeypatch):
    monkeypatch.delenv('OPENROAD_GDAL_ROOT', raising=False)
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    return tmp_path / 'openroadcode/tools/gdal/current'


def install(root):
    (root / 'bin').mkdir(parents=True)
    for name in TOOLS:
        tool = root / 'bin' / name
        tool.write_text('#!/bin/sh\nexit 0\n')
        tool.chmod(0o755)


def test_complete_private_installation_precedes_system_tools(installation, monkeypatch):
    install(installation)
    which = Mock(side_effect=AssertionError('must not use system GDAL'))
    monkeypatch.setattr('controllers.weather.gdal_tools.shutil.which', which)
    for name in TOOLS:
        assert gdal_tool(name) == str(installation / 'bin' / name)


def test_incomplete_or_broken_installation_never_mixes_system_tools(installation, monkeypatch):
    installation.parent.mkdir(parents=True)
    installation.symlink_to(installation.parent / 'missing-runtime')
    monkeypatch.setattr('controllers.weather.gdal_tools.shutil.which', Mock(return_value='/system/gdalinfo'))
    with pytest.raises(RuntimeError, match='incomplete'):
        gdal_tool('gdalinfo')


def test_explicit_override_is_used_and_failure_is_not_silently_ignored(installation, monkeypatch):
    custom = installation.parent / 'custom'
    monkeypatch.setenv('OPENROAD_GDAL_ROOT', str(custom))
    with pytest.raises(RuntimeError, match='incomplete'):
        gdal_tool('gdalinfo')
    install(custom)
    assert gdal_tool('gdalinfo') == str(custom / 'bin/gdalinfo')


def test_unconfigured_platform_falls_back_without_changing_environment(installation, monkeypatch):
    monkeypatch.setenv('PATH', '/unchanged')
    monkeypatch.setattr('controllers.weather.gdal_tools.shutil.which', Mock(return_value='/system/gdalwarp'))
    assert gdal_tool('gdalwarp') == '/system/gdalwarp'
    import os
    assert os.environ['PATH'] == '/unchanged'


def test_tile_commands_use_the_same_private_runtime(installation, monkeypatch):
    install(installation)
    run = Mock(return_value=Mock(returncode=0, stdout='metadata'))
    monkeypatch.setattr('controllers.weather.hrrr_tiles.subprocess.run', run)
    assert HrrrTileSource._run(['gdalinfo', '-json', '/field.grib2']) == 'metadata'
    assert run.call_args.args[0] == [str(installation / 'bin/gdalinfo'), '-json', '/field.grib2']
