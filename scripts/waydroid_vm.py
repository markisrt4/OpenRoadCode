# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Repeatable Ubuntu/X11 Waydroid VM lifecycle. Never run as root or in Termux."""
import argparse
import base64
import fcntl
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time

from scripts.setup_waydroid_location import setup as setup_location
from apps.launchers.waydroid_location_provider import configuration_path

ROOT = Path(__file__).resolve().parents[1]
RULE_COMMENT = 'openroadcode-waydroid'
BRIDGE = 'waydroid0'


def command(arguments, *, check=True, timeout=20, **kwargs):
    result = subprocess.run(arguments, text=True, capture_output=True, timeout=timeout, **kwargs)
    if check and result.returncode:
        raise RuntimeError(f'{arguments[0]} failed: {(result.stderr or result.stdout).strip()[:1200]}')
    return result


def interface_address(output):
    addresses = [ipaddress.IPv4Interface(item['local'] + '/' + str(item['prefixlen']))
                 for interface in json.loads(output) for item in interface.get('addr_info', [])
                 if item.get('family') == 'inet']
    if len(addresses) != 1:
        raise RuntimeError('Expected one IPv4 address on the Waydroid bridge.')
    return addresses[0]


def android_address(output):
    match = re.search(r'\binet\s+(\d+\.\d+\.\d+\.\d+/\d+)\b', output)
    if not match:
        raise RuntimeError('Android eth0 has no IPv4 address yet.')
    return ipaddress.IPv4Interface(match[1])


def process_identity(pid):
    """A PID plus Linux start ticks prevents signalling a reused process ID."""
    try:
        stat = (Path('/proc') / str(pid) / 'stat').read_text()
        return {'pid': int(pid), 'started': stat.rsplit(')', 1)[1].split()[19]}
    except (OSError, ValueError, IndexError):
        return None


def owned_process(record):
    return bool(record and process_identity(record['pid']) == record)


class WaydroidVM:
    def __init__(self, *, runner=command, sleeper=time.sleep):
        self.command, self.sleep = runner, sleeper
        self.runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
        self.state_path = self.runtime / 'openroadcode-waydroid-vm.json'
        self.log_dir = Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'openroadcode/waydroid-vm'
        self.display = os.environ.get('ORC_WAYDROID_DISPLAY', 'wayland-0')
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', self.display):
            raise RuntimeError('ORC_WAYDROID_DISPLAY must be a socket name, not a path.')
        self.environment = dict(os.environ, WAYLAND_DISPLAY=self.display,
                                ADB_LOCAL_TRANSPORT_MAX_PORT='5555')

    def out(self, *arguments, **kwargs):
        return self.command(list(arguments), **kwargs).stdout.strip()

    def android(self, *arguments, **kwargs):
        result = self.command(['sudo', '-n', 'waydroid', 'shell', '--', *arguments], **kwargs)
        output = (result.stdout + result.stderr).replace('\r', '')
        if kwargs.get('check', True) and re.search(r'Error:|Exception|RTNETLINK answers:|Unknown command|Permission denied', output):
            raise RuntimeError('Android command failed: ' + output.strip()[:800])
        return result.stdout.replace('\r', '').strip()

    def stage(self, message):
        print('[Waydroid] ' + message, flush=True)

    def state(self):
        try:
            state = json.loads(self.state_path.read_text())
        except FileNotFoundError:
            return {}
        if not isinstance(state, dict) or any(
            name not in {'display_launcher', 'session'} or not isinstance(record, dict)
            or type(record.get('pid')) is not int or record['pid'] <= 1
            or not isinstance(record.get('started'), str) or not record['started'].isdigit()
            for name, record in state.items()
        ):
            raise RuntimeError('Invalid managed runtime PID record; inspect it before stopping any processes.')
        return state

    def save(self, value):
        temporary = self.state_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value, indent=2))
        temporary.chmod(0o600)
        temporary.replace(self.state_path)

    def spawn(self, arguments, logfile):
        self.log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.log_dir / logfile
        with path.open('ab') as log:
            path.chmod(0o600)
            process = subprocess.Popen(arguments, cwd=ROOT, env=self.environment,
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        identity = process_identity(process.pid)
        if identity is None:
            raise RuntimeError(f'Could not start {arguments[0]}; inspect {path}')
        return identity

    def wait(self, description, predicate, attempts=30, timeout_s=None):
        last = ''
        deadline = time.monotonic() + (attempts if timeout_s is None else timeout_s)
        for _ in range(attempts):
            if time.monotonic() >= deadline:
                break
            try:
                result = predicate()
                if result:
                    return result
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                last = str(error)
            self.sleep(1)
        raise RuntimeError(f'Timed out waiting for {description}. {last}')

    def desktop_preflight(self):
        if not os.environ.get('DISPLAY') or not os.environ.get('XDG_RUNTIME_DIR') or not self.runtime.is_dir():
            raise RuntimeError('Start from the VM desktop terminal with DISPLAY and XDG_RUNTIME_DIR set.')
        for executable in ('waydroid', 'weston', 'adb', 'xdotool', 'xwininfo', 'ip'):
            if shutil.which(executable) is None:
                raise RuntimeError(f'{executable} is missing; run the install command first.')

    def display_ready(self):
        marker = self.runtime / 'openroadcode-waydroid-kiosk'
        try:
            pid = int(marker.read_text().strip())
            arguments = (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0')
            if not (self.runtime / self.display).exists() or not all(value in arguments for value in (
                b'--shell=kiosk-shell.so', b'--idle-time=0', ('--socket=' + self.display).encode())):
                return False
            windows = self.out('xdotool', 'search', '--class', '^Weston Compositor$', check=False).splitlines()
            if len(windows) != 1:
                return False
            # Weston 13's X11 backend publishes WM_CLASS but no _NET_WM_PID.
            # The marker's live process/arguments and socket were checked above.
            # Reject a contradictory PID when advertised, not an absent property.
            window_pid = self.out('xdotool', 'getwindowpid', windows[0], check=False)
            return not window_pid or window_pid == str(pid)
        except (OSError, ValueError):
            return False

    def start_runtime(self):
        self.desktop_preflight()
        if self.command(['sudo', '-n', 'test', '-s', '/var/lib/waydroid/waydroid.cfg'], check=False).returncode:
            raise RuntimeError('Android is not initialized. Run install --init-gapps first.')
        self.stage('Starting/reusing the dedicated kiosk display')
        state = self.state()
        if not self.display_ready():
            self.reclaim_stale_display()
            if (self.runtime / self.display).exists():
                raise RuntimeError('The selected Wayland socket belongs to an unverified/legacy compositor. '
                    'Stop its Waydroid session and that Weston instance once, then retry. No process was killed.')
            marker = self.runtime / 'openroadcode-waydroid-kiosk'
            if marker.exists():
                raise RuntimeError('A kiosk marker remains without a usable display. Check status and the Weston log before removing it.')
            state['display_launcher'] = self.spawn(['bash', str(ROOT / 'development/debian/start_waydroid_display.sh')], 'weston.log')
            self.save(state)
            self.wait('Weston kiosk socket', self.display_ready, attempts=15)
        self.stage('Starting the Android container and session')
        self.out('sudo', '-n', 'systemctl', 'start', 'waydroid-container')
        status = self.out('waydroid', 'status', env=self.environment)
        if not re.search(r'Session:\s*RUNNING', status):
            state['session'] = self.spawn(['waydroid', 'session', 'start'], 'session.log')
            self.save(state)
        self.wait('Android boot', lambda: self.android('getprop', 'sys.boot_completed') == '1', attempts=120)
        return state

    def reclaim_stale_display(self):
        """Reclaim only this user's dead socket, guarded by Wayland's own lock."""
        path = self.runtime / self.display
        marker = self.runtime / 'openroadcode-waydroid-kiosk'
        if marker.exists():
            try:
                pid = int(marker.read_text().strip())
            except ValueError:
                return
            if process_identity(pid) is not None:
                return
        if path.exists():
            info = path.lstat()
            if info.st_uid != os.getuid() or not stat.S_ISSOCK(info.st_mode):
                return
            try:
                with socket.socket(socket.AF_UNIX) as probe:
                    probe.settimeout(.5)
                    probe.connect(str(path))
                return  # A live compositor, including an unmarked legacy one.
            except ConnectionRefusedError:
                pass
            # Do not unlink a socket while a compositor is starting under lock.
            fd = os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                path.unlink()
            except BlockingIOError:
                return
            finally:
                os.close(fd)
        if marker.exists() and marker.lstat().st_uid == os.getuid() and not marker.is_symlink():
            marker.unlink()

    def network(self):
        """Use the bridge/subnet supplied by Waydroid, not a hard-coded guest IP."""
        bridge = interface_address(self.out('ip', '-j', '-4', 'addr', 'show', 'dev', BRIDGE))
        guest = android_address(self.android('ip', '-4', 'addr', 'show', 'eth0'))
        if guest.ip not in bridge.network or guest.ip == bridge.ip:
            raise RuntimeError('Android and the Waydroid bridge are not on the same subnet.')
        self.environment['ANDROID_SERIAL'] = f'{guest.ip}:5555'
        return bridge, guest

    def configure_network(self):
        self.stage('Checking the bridge and scoped forwarding/NAT rules')
        bridge, guest = self.network()
        route = json.loads(self.out('ip', '-j', 'route', 'get', str(guest.ip)))
        if not route or route[0].get('dev') != BRIDGE:
            raise RuntimeError('The host routes the Android address outside waydroid0. Resolve the overlapping route before retrying.')
        peer_index = int(self.android('cat', '/sys/class/net/eth0/iflink'))
        peers = json.loads(self.out('ip', '-j', 'link', 'show', 'master', BRIDGE))
        peer = next((item['ifname'] for item in peers if item['ifindex'] == peer_index), None)
        if peer is None:
            raise RuntimeError('Android has no matching host veth attached to waydroid0.')
        # Prevent NetworkManager from taking over these specific Waydroid links.
        # Never mark all veth* interfaces unmanaged: Docker also uses them.
        if shutil.which('nmcli') and self.command(['nmcli', '-t', '-f', 'RUNNING', 'general'], check=False).stdout.strip() == 'running':
            for device in (BRIDGE, peer):
                self.out('sudo', '-n', 'nmcli', 'device', 'set', device, 'managed', 'no')
        self.out('sudo', '-n', 'sysctl', '-w', 'net.ipv4.ip_forward=1')
        subnet = str(bridge.network)
        backends = [name for name in ('iptables', 'iptables-legacy') if shutil.which(name)]
        if not backends:
            raise RuntimeError('iptables is required for scoped Waydroid forwarding.')
        for backend in backends:
            for rule in (
                ['FORWARD', '-i', BRIDGE, '-s', subnet, '-m', 'comment', '--comment', RULE_COMMENT, '-j', 'ACCEPT'],
                ['FORWARD', '-o', BRIDGE, '-d', subnet, '-m', 'conntrack', '--ctstate', 'RELATED,ESTABLISHED',
                 '-m', 'comment', '--comment', RULE_COMMENT, '-j', 'ACCEPT'],
            ):
                prefix = ['sudo', '-n', backend, '-w', '5']
                if self.command(prefix + ['-C', *rule], check=False).returncode:
                    self.command(prefix + ['-I', rule[0], '1', *rule[1:]])
        # Waydroid often installs NAT in legacy tables while Docker uses nft.
        # Reuse existing subnet masquerading rather than adding competing NAT.
        existing = any(subnet in line and '-j MASQUERADE' in line
            for backend in backends
            for line in self.out('sudo', '-n', backend, '-w', '5', '-t', 'nat', '-S', 'POSTROUTING').splitlines())
        if not existing:
            self.out('sudo', '-n', backends[0], '-w', '5', '-t', 'nat', '-A', 'POSTROUTING',
                '-s', subnet, '!', '-d', subnet, '-m', 'comment', '--comment', RULE_COMMENT, '-j', 'MASQUERADE')
        # Android policy routing must have a connected route in the same table
        # before its gateway can be resolved. Do not add a catch-all policy rule.
        self.android('ip', 'route', 'replace', 'table', 'eth0', subnet, 'dev', 'eth0', 'scope', 'link', 'src', str(guest.ip))
        self.android('ip', 'route', 'replace', 'table', 'eth0', 'default', 'via', str(bridge.ip), 'dev', 'eth0')
        self.wait('host-to-Android reachability', lambda: self.command(
            ['ping', '-c', '1', '-W', '1', str(guest.ip)], check=False, timeout=3).returncode == 0, attempts=5)
        return bridge, guest

    def configure_adb(self, guest):
        self.stage('Authorizing this desktop user and verifying ADB')
        serial = f'{guest.ip}:5555'
        self.out('adb', 'start-server', env=self.environment)
        key = Path.home() / '.android/adbkey'
        if not key.exists():
            key.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.out('adb', 'keygen', str(key))
        public_path = key.with_suffix('.pub')
        if not public_path.exists():
            raise RuntimeError('The ADB public key is missing; recover adbkey.pub for the existing private key.')
        public = public_path.read_text().strip()
        try:
            if len(base64.b64decode(public.split()[0], validate=True)) != 524:
                raise ValueError('unexpected ADB public key size')
        except (ValueError, IndexError) as error:
            raise RuntimeError('Invalid desktop ADB public key; no Android keys changed.') from error
        existing = self.android('cat', '/data/misc/adb/adb_keys', check=False)
        changed = public not in existing.splitlines()
        if changed:
            # Preserve all existing keys and separate old unterminated lines.
            self.android('tee', '-a', '/data/misc/adb/adb_keys', input='\n' + public + '\n')
        self.android('chown', 'system:shell', '/data/misc/adb/adb_keys')
        self.android('chmod', '0640', '/data/misc/adb/adb_keys')
        if self.android('getenforce') != 'Disabled':
            self.android('restorecon', '/data/misc/adb/adb_keys')
        self.android('setprop', 'service.adb.tcp.port', '5555')
        listening = bool(re.search(r':5555\s', self.android('ss', '-lnt')))
        if changed or not listening or self.android('getprop', 'init.svc.adbd') != 'running':
            self.android('setprop', 'ctl.restart', 'adbd')
            self.sleep(1)
        if self.android('getprop', 'init.svc.adbd') == 'stopping':
            self.stage('Recovering the local Waydroid adbd stuck in stopping')
            self.android('killall', '-9', 'adbd', check=False)
            self.android('start', 'adbd')
        self.wait('Android adbd', lambda: self.android('getprop', 'init.svc.adbd') == 'running', attempts=10)
        def connected():
            if self.out('adb', '-s', serial, 'get-state', check=False, timeout=4) == 'device':
                return True
            self.out('adb', 'disconnect', serial, check=False)
            self.out('adb', 'connect', serial, check=False, timeout=12)
            return self.out('adb', '-s', serial, 'get-state', check=False, timeout=4) == 'device'
        self.wait('authorized Waydroid ADB (device, not offline/unauthorized)', connected, attempts=3, timeout_s=45)
        if 'waydroid' not in self.out('adb', '-s', serial, 'shell', 'getprop', 'ro.product.model').casefold():
            raise RuntimeError('ADB target is not Waydroid; location setup was not attempted.')
        return serial

    def configure(self):
        self.start_runtime()
        _, guest = self.configure_network()
        serial = self.configure_adb(guest)
        self.stage('Configuring Android kiosk and location sharing')
        self.android('locksettings', 'set-disabled', 'true')
        if self.android('locksettings', 'get-disabled') != 'true':
            raise RuntimeError('Android lock could not be disabled. A configured PIN/password must be handled in Android; it was not removed.')
        self.android('svc', 'power', 'stayon', 'true')
        setup_location('enable', serial)
        if self.out('adb', '-s', serial, 'shell', 'pm', 'path', 'com.waze', check=False).startswith('package:'):
            for permission in ('ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION'):
                self.out('adb', '-s', serial, 'shell', 'pm', 'grant', 'com.waze', 'android.permission.' + permission)
        else:
            self.stage('Waze is not installed. Install it inside Android, then rerun configure.')
        self.stage(f'Ready: {serial}. Host location still requires browser consent or a live GNSS source.')
        return serial

    def stop(self):
        state = self.state()
        if owned_process(state.get('session')):
            self.out('waydroid', 'session', 'stop', env=self.environment)
        launcher = state.get('display_launcher')
        if owned_process(launcher):
            os.kill(launcher['pid'], signal.SIGTERM)
        self.state_path.unlink(missing_ok=True)
        self.stage('Stopped owned session/display. Container service, apps and unrelated compositors preserved.')

    def restart(self):
        if not self.display_ready():
            raise RuntimeError('Restart requires the verified kiosk. Migrate a legacy display or run start first.')
        self.stage('Restarting Android and its virtual network; running Android apps will close')
        self.out('waydroid', 'session', 'stop', env=self.environment)
        self.wait('Android session to stop', lambda: not re.search(
            r'Session:\s*RUNNING', self.out('waydroid', 'status', env=self.environment)), attempts=15)
        self.out('sudo', '-n', 'systemctl', 'restart', 'waydroid-container')
        state = self.state()
        state.pop('session', None)
        self.save(state)

    def status(self):
        report = {'kiosk_ready': self.display_ready(), 'owned_processes': {
            name: owned_process(record) for name, record in self.state().items()}, 'log_directory': str(self.log_dir),
            'display_socket': str(self.runtime / self.display),
            'socket_exists': (self.runtime / self.display).exists(),
            'kiosk_marker_present': (self.runtime / 'openroadcode-waydroid-kiosk').exists()}
        if not shutil.which('waydroid'):
            report['installed'] = False
            return report
        report['installed'] = True
        result = self.command(['waydroid', 'status'], check=False)
        report['waydroid'] = result.stdout.strip()
        try:
            bridge, guest = self.network()
            report.update(bridge=str(bridge), android=str(guest), serial=f'{guest.ip}:5555')
            report['neighbors'] = self.out('ip', 'neigh', 'show', 'dev', BRIDGE)
            report['adbd'] = self.android('getprop', 'init.svc.adbd')
            report['android_lock_disabled'] = self.android('locksettings', 'get-disabled')
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
            report['network_error'] = str(error)
        # adb queries auto-start its daemon. A doctor/status command must not.
        try:
            with socket.create_connection(('127.0.0.1', 5037), timeout=.5):
                if 'serial' in report:
                    report['adb_state'] = self.out('adb', '-s', report['serial'], 'get-state', check=False)
        except OSError:
            report['adb_state'] = 'host ADB server is not running'
        try:
            location = json.loads(configuration_path().read_text())
            report['location_configured'] = location.get('enabled') is True
            report['location_matches_session'] = location.get('serial') == report.get('serial')
        except (OSError, ValueError):
            report['location_configured'] = False
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'start', 'configure', 'run', 'restart', 'status', 'stop'))
    parser.add_argument('--init-gapps', action='store_true', help='install only: initialize GAPPS if no Android image exists')
    args = parser.parse_args()
    if os.geteuid() == 0 or Path('/system/bin/am').exists():
        parser.error('Run as the normal Ubuntu VM desktop user; this is not a Termux launcher.')
    if args.init_gapps and args.action != 'install':
        parser.error('--init-gapps applies only to install')
    os.umask(0o077)
    try:
        vm = WaydroidVM()
        if args.action == 'install':
            subprocess.run(['bash', str(ROOT / 'development/debian/setup_waydroid.sh'),
                *(['--init-gapps'] if args.init_gapps else [])], check=True)
            return
        if args.action == 'status':
            print(json.dumps(vm.status(), indent=2))
            return
        if not vm.runtime.is_dir():
            raise RuntimeError('XDG_RUNTIME_DIR is unavailable; use the VM desktop terminal.')
        if args.action != 'stop':
            subprocess.run(['sudo', '-v'], check=True)
        with (vm.runtime / 'openroadcode-waydroid-vm.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            if args.action == 'stop':
                vm.stop()
                return
            if args.action == 'restart':
                vm.restart()
            vm.configure()
    except KeyboardInterrupt:
        parser.exit(130, 'Interrupted. Use stop to release managed session/display processes.\n')
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Waydroid setup failed: {error}\nRun status and inspect the stage logs; existing Android data was preserved.\n')


if __name__ == '__main__':
    main()
