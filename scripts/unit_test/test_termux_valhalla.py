# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Termux Valhalla startup relocates paths without modifying downloaded config."""

import json
import os
from pathlib import Path
import subprocess

from scripts.runtime.prepare_termux_valhalla import prepare


SCRIPT = Path(__file__).resolve().parents[1] / 'runtime/start_valhalla.sh'


def test_prepare_preserves_source_and_relocates_all_services(tmp_path):
    data, runtime = tmp_path / 'data', tmp_path / 'runtime'
    data.mkdir()
    (data / 'tiles.tar').touch()
    source = data / 'valhalla.json'
    config = {'mjolnir': {'tile_extract': '/build/tiles.tar', 'traffic_extract': '/data/valhalla/traffic.tar',
                          'landmarks': '/data/valhalla/landmarks.sqlite'},
              'loki': {'service': {'proxy': 'ipc:///tmp/loki'}},
              'httpd': {'service': {'loopback': 'ipc:///tmp/loopback', 'interrupt': 'ipc:///tmp/interrupt',
                                   'listen': 'tcp://*:8002'}},
              'logging': {'type': 'file', 'file_name': '/var/log/valhalla.log'}}
    source.write_text(json.dumps(config))
    original = source.read_bytes()
    output = runtime / 'prepared.json'
    prepare(source, output, data, runtime)
    result = json.loads(output.read_text())
    assert source.read_bytes() == original
    assert result['mjolnir']['tile_extract'] == str(data / 'tiles.tar')
    assert result['mjolnir']['traffic_extract'] == str(data / 'traffic.tar')
    assert result['mjolnir']['landmarks'] == str(data / 'landmarks.sqlite')
    assert result['loki']['service']['proxy'] == 'ipc://' + str(runtime / 'loki')
    assert result['httpd']['service']['loopback'] == 'ipc://' + str(runtime / 'loopback')
    assert result['httpd']['service']['listen'] == 'tcp://*:8002'
    assert result['logging']['file_name'] == str(runtime / 'valhalla.log')
    before = output.read_bytes()
    prepare(source, output, data, runtime)
    assert output.read_bytes() == before


def test_shell_termux_defaults_generate_config_and_execute_service(tmp_path):
    prefix = tmp_path / 'com.termux/usr'
    data = tmp_path / 'share/openroadcode/valhalla'
    data.mkdir(parents=True)
    source = data / 'valhalla.json'
    source.write_text(json.dumps({'mjolnir': {'tile_dir': '/data/valhalla/tiles'},
                                 'thor': {'service': {'proxy': 'ipc:///tmp/thor'}}}))
    binary = prefix / 'opt/openroadcode/navigation/valhalla/bin/valhalla_service'
    binary.parent.mkdir(parents=True)
    binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    binary.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if not key.startswith('VALHALLA_')}
    env.update(PREFIX=str(prefix), XDG_DATA_HOME=str(tmp_path / 'share'), TERMUX_VERSION='test')
    result = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, check=True)
    config_path, workers = result.stdout.strip().splitlines()
    assert workers == '1'
    generated = json.loads(Path(config_path).read_text())
    assert generated['thor']['service']['proxy'] == 'ipc://' + str(prefix / 'tmp/openroadcode-valhalla/thor')
    assert json.loads(source.read_text())['thor']['service']['proxy'] == 'ipc:///tmp/thor'


def test_linux_explicit_config_is_passed_through_unchanged(tmp_path):
    source = tmp_path / 'config.json'
    source.write_text('{}')
    binary = tmp_path / 'service'
    binary.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
    binary.chmod(0o755)
    env = {key: value for key, value in os.environ.items() if key not in ('PREFIX', 'TERMUX_VERSION')}
    env.update(VALHALLA_CONFIG=str(source), VALHALLA_BIN=str(binary), VALHALLA_WORKERS='2')
    result = subprocess.run(['bash', str(SCRIPT)], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.splitlines() == [str(source), '2']
    assert source.read_text() == '{}'


def test_termux_installer_registers_routing_service_and_log_supervisor(tmp_path):
    prefix = tmp_path / 'usr'
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    sv = binaries / 'sv'
    sv.write_text('#!/bin/sh\nexit 0\n')
    sv.chmod(0o755)
    for name in ('openroadcode-service-manager', 'openroadcode-message-broker',
                 'openroadcode-valhalla', 'openroadcode-navigation',
                 'openroadcode-automotive', 'openroadcode-adsb'):
        supervise = prefix / 'var/service' / name / 'supervise'
        supervise.mkdir(parents=True)
        (supervise / 'ok').touch()
    env = dict(os.environ, PREFIX=str(prefix), PATH=str(binaries) + ':' + os.environ['PATH'])
    installer = SCRIPT.parents[1] / 'runit/install_termux_services.sh'
    subprocess.run(['bash', str(installer)], env=env, capture_output=True, text=True, check=True)
    installed = prefix / 'var/service/openroadcode-valhalla'
    assert 'start_valhalla.sh' in (installed / 'run').read_text()
    assert 'svlogd' in (installed / 'log/run').read_text()
    assert (installed / 'down').exists()
    assert not (prefix / 'var/service/openroadcode-service-manager/down').exists()
    assert os.access(installed / 'run', os.X_OK)
    assert os.access(installed / 'log/run', os.X_OK)
