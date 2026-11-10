"""Host-side entry to existing offline installers and explicit Actions requests."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

REPOSITORY = 'markisrt4/OpenRoadCode'
WORKFLOW = 'build-metro-detroit-imagery.yml'
ROOT = Path(__file__).resolve().parents[3]
BUILD_TARGETS = (
    ('Metro Detroit imagery and terrain', 'metro-detroit'),
    ('Michigan buildings (eight regions)', 'michigan-buildings'),
    ('Detroit / Auburn Hills / Rochester detail pilot', 'michigan-detail-pilot'),
    ('State overview imagery and terrain (not roads/routing)', 'generic-state'),
)


def choose(title, labels):
    print('\n' + title)
    for index, label in enumerate(labels, 1):
        print(f'  {index}. {label}')
    while True:
        answer = input('Choose a number (Enter cancels): ').strip()
        if not answer:
            return None
        if answer.isascii() and answer.isdigit() and 1 <= int(answer) <= len(labels):
            return int(answer) - 1
        print('Choose one of the listed numbers.')


def build_command(target, branch, state=None):
    """Keep workflow selection explicit; never infer a costly statewide build."""
    if target not in {value for _, value in BUILD_TARGETS}:
        raise ValueError('Unsupported build target')
    if not branch or branch.startswith('-'):
        raise ValueError('Select a checked-out feature branch')
    command = ['gh', 'workflow', 'run', WORKFLOW, '--repo', REPOSITORY,
               '--ref', branch, '-f', 'build_target=' + target]
    if target == 'generic-state':
        from development.maps.state_map_catalog import state_plan
        abbreviation = state_plan(state or '')['abbreviation']
        command += ['-f', 'state=' + abbreviation, '-f', 'scope=overview']
    return command


def request_build():
    if not shutil.which('gh'):
        print('GitHub CLI (gh) is required only for requesting builds. No build requested.')
        return 1
    selection = choose('Request an existing GitHub Actions build', [label for label, _ in BUILD_TARGETS])
    if selection is None:
        return 0
    target = BUILD_TARGETS[selection][1]
    state = input('State name or abbreviation: ').strip() if target == 'generic-state' else None
    branch = subprocess.run(['git', 'branch', '--show-current'], cwd=ROOT,
                            check=True, capture_output=True, text=True).stdout.strip()
    command = build_command(target, branch, state)
    print(f'Repository: {REPOSITORY} · branch: {branch}')
    print('Build size is unknown until processing finishes. This consumes Actions resources.')
    print('Builds do not install data. Finished packs must be downloaded and verified separately.')
    if input('Request this cloud build? [y/N] ').strip().lower() != 'y':
        print('Cancelled; no build requested.')
        return 0
    subprocess.run(['gh', 'auth', 'status'], check=True, cwd=ROOT)
    subprocess.run(command, check=True, cwd=ROOT)
    print(f'Build requested. Monitor: https://github.com/{REPOSITORY}/actions')
    return 0


def main():
    print('ORC offline map packs')
    print('Reuse published/downloaded packs first. Installation uses existing verification and activation.')
    print('Nationwide coarse terrain: planned; not yet built or sized.')
    print('Roads/search/routing: existing navigation builder; cross-state routing still needs verification.')
    selection = choose('Choose an operation', (
        'Install published Metro Detroit imagery (existing release installer)',
        'Install terrain from a published descriptor',
        'Install downloaded Michigan building packs',
        'Request a cloud build (GitHub authentication and repository permission required)',
    ))
    if selection is None:
        return 0
    try:
        if selection == 3:
            return request_build()
        if selection == 0:
            tag = input('Published release tag (Enter cancels): ').strip()
            if not tag:
                return 0
            arguments = ['development.maps.install_region', '--coverage', 'metro-detroit',
                         '--github-release', tag]
        elif selection == 1:
            coverage = input('Coverage ID (Enter cancels): ').strip()
            if not coverage:
                return 0
            descriptor = input('Published HTTPS .zip.json URL (Enter cancels): ').strip()
            if not descriptor:
                return 0
            if not descriptor.startswith('https://'):
                raise ValueError('A published HTTPS descriptor is required; source downloading is not selected')
            arguments = ['development.maps.install_terrain', '--coverage', coverage,
                         '--pack-manifest', descriptor]
        else:
            directory = input('Downloaded Michigan buildings directory (Enter cancels): ').strip()
            if not directory:
                return 0
            arguments = ['development.maps.install_buildings', '--michigan-directory', directory]
        # Each existing installer retains ownership of checksums, limits and activation.
        return subprocess.run([sys.executable, '-m', *arguments], cwd=ROOT, check=False).returncode
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Map pack operation failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
