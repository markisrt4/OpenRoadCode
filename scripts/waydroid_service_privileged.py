#!/usr/bin/python3 -I
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Installed root-owned helper. Fixed Waydroid operations; no checkout imports."""
import base64
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import time


def run(*arguments, check=True, input=None):
    result = subprocess.run(arguments, input=input, text=True, capture_output=True, timeout=25, check=False)
    output = result.stdout + result.stderr
    if check and (result.returncode or re.search(r'Error:|Exception|Permission denied|RTNETLINK answers:|Unknown command', output)):
        raise RuntimeError(f'{arguments[0]} failed: {output.strip()[:800]}')
    return result


def android(*arguments, **kwargs):
    return run('waydroid', 'shell', '--', *arguments, **kwargs).stdout.strip()


def prepare_network():
    entries = json.loads(run('ip', '-j', '-4', 'addr', 'show', 'dev', 'waydroid0').stdout)
    addresses = [ipaddress.IPv4Interface(item['local'] + '/' + str(item['prefixlen']))
        for entry in entries for item in entry.get('addr_info', []) if item.get('family') == 'inet']
    if len(addresses) != 1:
        raise RuntimeError('Expected one Waydroid bridge address')
    bridge = addresses[0]
    match = re.search(r'\binet\s+(\d+\.\d+\.\d+\.\d+/\d+)', android('ip', '-4', 'addr', 'show', 'eth0'))
    if not match:
        raise RuntimeError('Android eth0 has no address')
    guest = ipaddress.IPv4Interface(match[1])
    if guest.ip not in bridge.network or guest.ip == bridge.ip:
        raise RuntimeError('Android and bridge subnet mismatch')
    routes = json.loads(run('ip', '-j', 'route', 'get', str(guest.ip)).stdout)
    if not routes or routes[0].get('dev') != 'waydroid0':
        raise RuntimeError('Conflicting route to Android; expected waydroid0')
    index = int(android('cat', '/sys/class/net/eth0/iflink'))
    peers = json.loads(run('ip', '-j', 'link', 'show', 'master', 'waydroid0').stdout)
    peer = next((item['ifname'] for item in peers if item['ifindex'] == index), None)
    if peer is None:
        raise RuntimeError('Android veth is not attached to waydroid0')
    if shutil.which('nmcli') and run('nmcli', '-t', '-f', 'RUNNING', 'general', check=False).stdout.strip() == 'running':
        for device in ('waydroid0', peer):
            run('nmcli', 'device', 'set', device, 'managed', 'no')
    run('sysctl', '-w', 'net.ipv4.ip_forward=1')
    subnet = str(bridge.network)
    backends = [name for name in ('iptables', 'iptables-legacy') if shutil.which(name)]
    if not backends:
        raise RuntimeError('iptables is missing')
    for backend in backends:
        for rule in (
            ['FORWARD', '-i', 'waydroid0', '-s', subnet, '-m', 'comment', '--comment', 'openroadcode-waydroid', '-j', 'ACCEPT'],
            ['FORWARD', '-o', 'waydroid0', '-d', subnet, '-m', 'conntrack', '--ctstate', 'RELATED,ESTABLISHED',
             '-m', 'comment', '--comment', 'openroadcode-waydroid', '-j', 'ACCEPT'],
        ):
            if run(backend, '-w', '5', '-C', *rule, check=False).returncode:
                run(backend, '-w', '5', '-I', rule[0], '1', *rule[1:])
    existing = any(subnet in line and '-j MASQUERADE' in line for backend in backends
        for line in run(backend, '-w', '5', '-t', 'nat', '-S', 'POSTROUTING').stdout.splitlines())
    if not existing:
        run(backends[0], '-w', '5', '-t', 'nat', '-A', 'POSTROUTING', '-s', subnet, '!', '-d', subnet,
            '-m', 'comment', '--comment', 'openroadcode-waydroid', '-j', 'MASQUERADE')
    android('ip', 'route', 'replace', 'table', 'eth0', subnet, 'dev', 'eth0', 'scope', 'link', 'src', str(guest.ip))
    android('ip', 'route', 'replace', 'table', 'eth0', 'default', 'via', str(bridge.ip), 'dev', 'eth0')
    return str(guest.ip)


def authorize(home):
    with (home / '.android/adbkey.pub').open() as stream:
        public = stream.read(16385).strip()
    if len(public) > 16384 or '\n' in public or '\r' in public:
        raise RuntimeError('Invalid ADB public key')
    if not public or len(base64.b64decode(public.split()[0], validate=True)) != 524:
        raise RuntimeError('Invalid ADB public key')
    existing = android('cat', '/data/misc/adb/adb_keys', check=False)
    changed = public not in existing.splitlines()
    if changed:
        android('tee', '-a', '/data/misc/adb/adb_keys', input='\n' + public + '\n')
    android('chown', 'system:shell', '/data/misc/adb/adb_keys')
    android('chmod', '0640', '/data/misc/adb/adb_keys')
    if android('getenforce') != 'Disabled':
        android('restorecon', '/data/misc/adb/adb_keys')
    android('setprop', 'service.adb.tcp.port', '5555')
    if changed or android('getprop', 'init.svc.adbd') != 'running' or not re.search(r':5555\s', android('ss', '-lnt')):
        android('setprop', 'ctl.restart', 'adbd')
        time.sleep(1)
    if android('getprop', 'init.svc.adbd') == 'stopping':
        android('killall', '-9', 'adbd', check=False)
        android('start', 'adbd')


def main():
    if os.geteuid() != 0 or len(sys.argv) != 2 or sys.argv[1] not in {'container', 'prepare', 'location-root', 'location-shell'}:
        raise SystemExit('Use the installed Waydroid user service')
    uid = int(os.environ.get('SUDO_UID', '0'))
    if uid <= 0:
        raise SystemExit('A normal desktop sudo identity is required')
    home = Path(pwd.getpwuid(uid).pw_dir)
    # All child commands use administrator-controlled executables, never PATH
    # or Python modules from the invoking user's checkout.
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    os.chdir('/')
    if sys.argv[1] == 'container':
        if not Path('/var/lib/waydroid/waydroid.cfg').is_file():
            raise RuntimeError('Initialize Waydroid before installing services')
        run('systemctl', 'start', 'waydroid-container.service')
    elif sys.argv[1] == 'prepare':
        for _ in range(120):
            if (android('getprop', 'sys.boot_completed', check=False) == '1'
                    and re.search(r'\binet\s+\d+\.\d+\.\d+\.\d+/',
                        android('ip', '-4', 'addr', 'show', 'eth0', check=False))):
                break
            time.sleep(1)
        else:
            raise RuntimeError('Android boot/network address timed out')
        address = prepare_network()
        authorize(home)
        android('locksettings', 'set-disabled', 'true')
        if android('locksettings', 'get-disabled') != 'true':
            raise RuntimeError('Android has a secure lock; remove it in Android first')
        android('svc', 'power', 'stayon', 'true')
        print(json.dumps({'address': address}))
    else:
        mock_uid = '0' if sys.argv[1] == 'location-root' else '2000'
        android('cmd', 'appops', 'set', mock_uid, 'android:mock_location', 'allow')
        android('cmd', 'location', 'set-location-enabled', 'true', '--user', '0')
        if android('pm', 'path', 'com.waze', check=False).startswith('package:'):
            for permission in ('ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION'):
                android('pm', 'grant', 'com.waze', 'android.permission.' + permission)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(str(error)) from error
