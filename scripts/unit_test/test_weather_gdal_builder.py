# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Exercise builder reuse and resume with fake native tools, not a GDAL build."""
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / 'development/termux/build_weather_gdal.sh'


@pytest.fixture
def setup(tmp_path):
    env = dict(os.environ, TERMUX_VERSION='test', PREFIX=str(tmp_path / 'prefix'),
               TMPDIR=str(tmp_path), XDG_DATA_HOME=str(tmp_path / 'data'),
               XDG_STATE_HOME=str(tmp_path / 'state'), XDG_CACHE_HOME=str(tmp_path / 'cache'))
    fake = tmp_path / 'bin'
    fake.mkdir()
    env['PATH'] = str(fake) + os.pathsep + os.environ['PATH']
    marker = tmp_path / 'pkg-called'
    (fake / 'pkg').write_text(f'#!/bin/sh\ntouch "{marker}"\nexit 77\n')
    (fake / 'pkg').chmod(0o755)
    root = tmp_path / 'data/openroadcode/tools/gdal'
    candidate = root / 'gdal-3.13.3.ABCDEF'
    (candidate / 'bin').mkdir(parents=True)
    for name in ('gdalinfo', 'gdal_translate', 'gdalwarp'):
        tool = candidate / 'bin' / name
        tool.write_text('''#!/bin/sh
if [ "$1" = --version ]; then echo 'GDAL 3.13.3 "test", released 2026'; exit 0; fi
if [ "$1" = --format ]; then exit "${FAIL_DRIVER_CHECK:-0}"; fi
if [ "$1" = -json ]; then
  echo '{"size":[8,8],"bands":[{"minimum":10,"maximum":40}]}'
fi
''')
        tool.chmod(0o755)
    (root / 'current').symlink_to(candidate)
    return tmp_path, env, root, candidate, marker


def run(env, *arguments):
    return subprocess.run(['bash', str(SCRIPT), *arguments], env=env,
                          text=True, capture_output=True, timeout=10)


def test_healthy_installation_skips_packages_and_build(setup):
    tmp, env, root, candidate, marker = setup
    result = run(env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'no build needed' in result.stdout
    assert not marker.exists()
    assert (root / 'current').resolve() == candidate
    assert not (tmp / 'state/openroadcode/gdal/build-3.13.3').exists()


def test_failed_installed_check_does_not_start_a_build_loop(setup):
    _, env, root, candidate, marker = setup
    env['FAIL_DRIVER_CHECK'] = '9'
    result = run(env)
    assert result.returncode != 0
    assert '--rebuild' in result.stderr
    assert not marker.exists()
    assert (root / 'current').resolve() == candidate


def test_explicit_rebuild_bypasses_healthy_installation_check(setup):
    _, env, root, candidate, marker = setup
    result = run(env, '--rebuild')
    assert result.returncode == 77  # Fake package installer stops before any build.
    assert marker.exists()
    assert (root / 'current').resolve() == candidate


def prepare_configuration_failure(setup):
    tmp, _, _, candidate, _ = setup
    fake = tmp / 'bin'
    for name, content in (
        ('pkg', 'exit 0'), ('sha256sum', 'exit 0'),
        ('cmake', f'printf "%s\\n" "$@" > "{tmp}/cmake-args"\nexit 78'),
    ):
        tool = fake / name
        tool.write_text('#!/bin/sh\n' + content + '\n')
        tool.chmod(0o755)
    build = tmp / 'state/openroadcode/gdal/build-3.13.3'
    build.mkdir(parents=True)
    (build / 'CMakeCache.txt').write_text(f'CMAKE_INSTALL_PREFIX:PATH={candidate}/runtime\n')
    source = tmp / 'state/openroadcode/gdal/source/gdal-3.13.3'
    source.mkdir(parents=True)
    (source / 'CMakeLists.txt').touch()
    cache = tmp / 'cache/openroadcode/gdal'
    cache.mkdir(parents=True)
    (cache / 'gdal-3.13.3.tar.xz').touch()


def test_interrupted_build_keeps_original_prefix(setup):
    tmp, env, root, candidate, _ = setup
    (root / 'current').unlink()
    prepare_configuration_failure(setup)
    result = run(env)
    assert result.returncode == 78, result.stdout + result.stderr
    assert 'Resuming existing build candidate' in result.stdout
    assert f'-DCMAKE_INSTALL_PREFIX={candidate}/runtime' in (tmp / 'cmake-args').read_text()
    assert len(list(root.glob('gdal-3.13.3.*'))) == 1
    assert not (root / 'current').exists()


def test_forced_rebuild_never_reuses_active_install_directory(setup):
    tmp, env, root, candidate, _ = setup
    prepare_configuration_failure(setup)
    result = run(env, '--rebuild')
    assert result.returncode == 78, result.stdout + result.stderr
    assert f'-DCMAKE_INSTALL_PREFIX={candidate}/runtime' not in (tmp / 'cmake-args').read_text()
    assert (root / 'current').resolve() == candidate
    assert len(list(root.glob('gdal-3.13.3.*'))) == 2
