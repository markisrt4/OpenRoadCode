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



def edit_layers(selected, area, title):
    from .map_pack_selection import LAYERS, Selection, toggle
    while True:
        labels = [f"[{'x' if Selection(area, i) in selected else ' '}] {label}"
                  for i, label in enumerate(LAYERS)]
        answer = choose(title + ' — toggle layers; Enter returns', labels)
        if answer is None:
            return
        toggle(selected, area, answer)


def edit_michigan(selected):
    from .map_pack_selection import AREAS, MICHIGAN_AREAS, METRO_AREAS
    while True:
        answer = choose('Michigan — add any combination of areas',
                        [AREAS[key] for key in MICHIGAN_AREAS])
        if answer is None:
            return
        area = MICHIGAN_AREAS[answer]
        if area != 'metro-detroit':
            edit_layers(selected, area, AREAS[area])
            continue
        while True:
            metro = choose('Metro Detroit', ('Whole Metro Detroit area',
                                             'Customize smaller areas'))
            if metro is None:
                break
            if metro == 0:
                edit_layers(selected, area, AREAS[area])
            else:
                child = choose('Within Metro Detroit', [AREAS[key] for key in METRO_AREAS])
                if child is not None:
                    key = METRO_AREAS[child]
                    edit_layers(selected, key, AREAS[key])


def review(selected):
    from .map_pack_selection import AREAS, LAYERS, effective_selection
    effective = effective_selection(selected)
    if not effective:
        print('No layers selected.')
        return
    print('\nYour combined selection')
    for item in effective:
        print(f'  {AREAS.get(item.area, item.area)} · {LAYERS[item.layer]}')
    if len(effective) < len(selected):
        print('Overlapping layers are included under their larger selected area.')
    print('Nationwide basic terrain is planned; no downloadable pack exists yet.')
    print('Roads/search/routing still use the existing navigation builder.')
    print('Download and installed sizes are unknown until published descriptors are checked.')
    print('Other regional packs may require a build; selecting an area does not start one.')
    action = choose('Review actions', (
        'Check published Metro Detroit downloads for selected layers',
        'Request a cloud build — review available build bundles',
        'Return to selections',
    ))
    if action == 0:
        install_published(effective)
    elif action == 1:
        request_build()


def install_published(selected):
    # Reuse release discovery and descriptor verification; never source-build on failure.
    from development.maps.prebuilt_imagery import github_release_descriptor, read_descriptor
    supported = [item for item in selected if item.area == 'metro-detroit' and item.layer in (1, 4)]
    if not supported:
        print('No published-download integration for these layers yet. No data changed.')
        return
    imagery_url = github_release_descriptor('latest')
    candidates = []
    for item in supported:
        terrain = item.layer == 1
        url = (imagery_url.rsplit('/', 1)[0] + '/metro-detroit-terrain.zip.json'
               if terrain else imagery_url)
        descriptor, _ = read_descriptor(url, 'metro-detroit')
        if terrain and descriptor.get('kind') != 'terrain':
            raise ValueError('Published terrain descriptor has the wrong kind')
        candidates.append((terrain, url))
        print(f"Metro Detroit {'terrain' if terrain else 'imagery'}: "
              f"{descriptor['bytes'] / 1048576:.1f} MiB download")
    print('Only the listed Metro Detroit layers will install; other selections remain pending.')
    if input('Download and install these published packs? [y/N] ').strip().lower() != 'y':
        return
    for terrain, url in candidates:
        module = 'development.maps.install_terrain' if terrain else 'development.maps.install_region'
        subprocess.run([sys.executable, '-m', module, '--coverage', 'metro-detroit',
                        '--pack-manifest', url], cwd=ROOT, check=True)


def main():
    selected = set()
    print('ORC offline maps — selections from different areas can be combined.')
    print('Choose areas and layers first. Review availability before downloading or requesting builds.')
    try:
        while True:
            answer = choose(f'Your offline maps · {len(selected)} layer selections', (
                'United States — basic terrain',
                'Michigan — statewide and major areas',
                'Add another state',
                'Review selections / downloads',
            ))
            if answer is None:
                print('Closed; selections are not saved. Completed installations are retained.')
                return 0
            if answer == 0:
                from .map_pack_selection import Selection, toggle
                print('Nationwide basic terrain is planned, not available for installation yet.')
                current = Selection('us', 1) in selected
                if input(f"{'Remove' if current else 'Add'} to selection? [y/N] ").strip().lower() == 'y':
                    toggle(selected, 'us', 1)
            elif answer == 1:
                edit_michigan(selected)
            elif answer == 2:
                from development.maps.state_map_catalog import state_plan
                value = input('State name or abbreviation (Enter returns): ').strip()
                if value:
                    state = state_plan(value)
                    if state['abbreviation'] == 'MI':
                        edit_michigan(selected)
                    else:
                        edit_layers(selected, state['abbreviation'], state['name'])
            else:
                review(selected)
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled.')
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'Map pack operation failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
