# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Install Ubuntu/X11 user services; never launch the dashboard implicitly."""
import argparse
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HELPER = '/usr/local/libexec/openroadcode-waydroid-prepare'
UNITS = ('openroadcode-waydroid.service', 'openroadcode-ui.service', 'openroadcode-session.target')


def systemd_quote(value, *, command=False):
    value = str(value)
    if '\n' in value or '\r' in value:
        raise ValueError('Newlines in installation paths are unsupported')
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%')
    return '"' + (value.replace('$', '$$') if command else value) + '"'


def desktop_quote(value):
    systemd_quote(value)  # Reject embedded newlines before writing an entry.
    escaped = ''.join('\\' + char if char in '\\"`$' else char for char in str(value))
    # Desktop entries first unescape string values, then parse Exec arguments.
    return '"' + escaped.replace('\\', '\\\\').replace('%', '%%') + '"'


def sudoers(user):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*\$?', user):
        raise ValueError('Unsupported desktop account name for the scoped sudo rule')
    return ''.join(f'{user} ALL=(root) NOPASSWD: {HELPER} {action}\n'
        for action in ('container', 'prepare', 'location-root', 'location-shell'))


def render(name):
    text = (ROOT / 'development/debian/systemd' / name).read_text()
    for token, value in {'PROJECT': ROOT, 'PYTHON': sys.executable, 'LAUNCHER': ROOT / 'runOrcUi'}.items():
        quoted = systemd_quote(value, command=token != 'PROJECT')
        # WorkingDirectory is a single path value, not a shell/argv list. It
        # accepts spaces directly and treats surrounding quotes as path bytes.
        if token == 'PROJECT':
            quoted = str(value).replace('%', '%%')
        text = text.replace('@' + token + '@', quoted)
    return text


def run(*arguments):
    subprocess.run(arguments, check=True, timeout=120)


def install(autostart_orc=False):
    user = pwd.getpwuid(os.getuid()).pw_name
    rules = sudoers(user)
    rendered = {name: render(name) for name in UNITS}
    active = subprocess.run(['systemctl', '--user', 'is-active', 'openroadcode-waydroid.service'],
        capture_output=True, text=True, check=False, timeout=15)
    if active.stdout.strip() in {'active', 'activating', 'deactivating', 'reloading'}:
        raise RuntimeError('Stop openroadcode-session.target and openroadcode-waydroid.service before upgrading services')
    run('sudo', '-v')
    run('sudo', 'test', '-s', '/var/lib/waydroid/waydroid.cfg')
    subprocess.run(['systemctl', '--user', 'show-environment'], stdout=subprocess.DEVNULL, check=True, timeout=15)
    # Privileged code is copied to an administrator-owned directory. The sudo
    # grant never runs Python or shell code from the user-writable checkout.
    run('sudo', 'install', '-d', '-m', '0755', '-o', 'root', '-g', 'root', '/usr/local/libexec')
    run('sudo', 'install', '-m', '0755', '-o', 'root', '-g', 'root',
        str(ROOT / 'scripts/waydroid_service_privileged.py'), HELPER)
    with tempfile.TemporaryDirectory(prefix='orc-waydroid-services-') as temporary:
        path = Path(temporary) / 'sudoers'
        path.write_text(rules)
        run('sudo', 'visudo', '-cf', str(path))
        destination = '/etc/sudoers.d/openroadcode-waydroid-' + user
        run('sudo', 'install', '-m', '0440', '-o', 'root', '-g', 'root', str(path), destination)
        run('sudo', 'visudo', '-cf', destination)
    run('sudo', 'systemctl', 'enable', '--now', 'waydroid-container.service')
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    units = config / 'systemd/user'
    units.mkdir(parents=True, exist_ok=True)
    for name in UNITS:
        (units / name).write_text(rendered[name])
    autostart = config / 'autostart'
    autostart.mkdir(parents=True, exist_ok=True)
    (autostart / 'openroadcode-waydroid.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=OpenRoadCode Waydroid runtime\n'
        'Exec=/bin/bash ' + desktop_quote(ROOT / 'development/debian/start_waydroid_services.sh') + '\n'
        'Terminal=false\n')
    run('systemctl', '--user', 'daemon-reload')
    if autostart_orc:
        run('systemctl', '--user', 'enable', 'openroadcode-ui.service')
    print('Services installed; ORC and its user runtime were not launched. Start from the X11 desktop with:')
    print('bash development/debian/start_waydroid_services.sh')


def uninstall():
    user = pwd.getpwuid(os.getuid()).pw_name
    sudoers(user)  # Validate before constructing the administrator-owned path.
    run('systemctl', '--user', 'stop', 'openroadcode-session.target', 'openroadcode-ui.service', 'openroadcode-waydroid.service')
    run('systemctl', '--user', 'disable', 'openroadcode-ui.service', 'openroadcode-waydroid.service')
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    for name in UNITS:
        (config / 'systemd/user' / name).unlink(missing_ok=True)
    (config / 'autostart/openroadcode-waydroid.desktop').unlink(missing_ok=True)
    run('systemctl', '--user', 'daemon-reload')
    run('sudo', 'rm', '-f', '/etc/sudoers.d/openroadcode-waydroid-' + user)
    print('User services and sudo grant removed; Android data/container and shared root helper preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'uninstall'))
    parser.add_argument('--autostart-orc', action='store_true', help='install only: opt in to dashboard startup at desktop login')
    args = parser.parse_args()
    if os.geteuid() == 0 or Path('/system/bin/am').exists():
        parser.error('Run as the normal Ubuntu X11 desktop user, not root or Termux')
    if args.autostart_orc and args.action != 'install':
        parser.error('--autostart-orc applies only to install')
    try:
        if args.action == 'install':
            install(args.autostart_orc)
        else:
            uninstall()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        raise SystemExit(f'Service installation failed: {error}') from error


if __name__ == '__main__':
    main()
