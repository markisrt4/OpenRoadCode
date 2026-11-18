"""Download successful US terrain states independently, retaining verified progress."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time

from development.maps.prebuilt_imagery import read_local_archive
from development.maps.state_map_catalog import state_plan
from tools.map_builder.builder.terrain_artifact import MAX_ARCHIVE_BYTES

REPOSITORY = 'markisrt4/OpenRoadCode'


def pages(run, resource, field):
    result = subprocess.check_output(['gh', 'api', '--paginate', '--slurp',
        f'repos/{REPOSITORY}/actions/runs/{run}/{resource}?per_page=100'], text=True)
    return [item for page in json.loads(result) for item in page[field]]


def successful_states(jobs):
    states = set()
    for job in jobs:
        match = re.search(r'(?:^|/ )state \(([A-Z]{2})\)$', job['name'])
        if match and job['conclusion'] == 'success':
            states.add(match[1])
    return sorted(states)


def checked_archive(archive, coverage, bounds):
    descriptor, archive = read_local_archive(archive, coverage, max_archive_bytes=MAX_ARCHIVE_BYTES)
    if descriptor.get('kind') != 'terrain' or descriptor.get('bounds_deg') != list(bounds):
        raise ValueError('Terrain kind or bounds mismatch')
    return descriptor, archive


def fetch_state(run, state, output, reuse, *, attempts=3):
    regions = state_plan(state)['overview_regions']
    destination = output/state
    destination.mkdir(parents=True, exist_ok=True)
    roots = [output, *reuse]
    needed = []
    for region in regions:
        coverage = region['coverage']; found = None
        for root in roots:
            for archive in root.rglob(coverage+'-terrain.zip') if root.is_dir() else []:
                try:
                    found = checked_archive(archive, coverage, region['bounds_deg'])
                except (OSError, ValueError, KeyError):
                    continue
                break
            if found:
                break
        if found:
            descriptor, archive = found
            target = destination/archive.name
            if archive.resolve() != target.resolve():
                shutil.copy2(archive, target)
            target.with_suffix('.zip.json').write_text(json.dumps(descriptor, indent=2))
            print(f'{state}: verified local {archive.name}; no download', flush=True)
        else:
            needed.append(region)
    if not needed:
        return
    for attempt in range(1, attempts+1):
        try:
            with TemporaryDirectory(dir=output, prefix='.state-download-') as temporary:
                subprocess.run(['gh', 'run', 'download', str(run), '--repo', REPOSITORY,
                    '--name', f'us-coarse-terrain-{state}-{run}', '--dir', temporary],
                    check=True, timeout=300)
                # Preflight all required archives before retaining this state's selection.
                checked = [checked_archive(Path(temporary)/(region['coverage']+'-terrain.zip'),
                            region['coverage'], region['bounds_deg']) for region in needed]
                for descriptor, archive in checked:
                    shutil.move(archive, destination/archive.name)
                    (destination/(archive.name+'.json')).write_text(json.dumps(descriptor, indent=2))
                report = Path(temporary)/'us-terrain-report.json'
                if report.is_file():
                    shutil.copy2(report, destination/report.name)
            return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError):
            if attempt == attempts:
                raise
            print(f'{state}: transfer/verification failed; retry {attempt}/{attempts-1}', flush=True)
            time.sleep(min(30, 5*attempt))


def download(run, output, reuse=(), *, attempts=3):
    if not str(run).isdigit() or not 1 <= attempts <= 10:
        raise ValueError('Numeric run and 1–10 attempts required')
    subprocess.run(['gh', 'auth', 'status'], check=True)
    states = successful_states(pages(run, 'jobs', 'jobs'))
    available = {item['name'] for item in pages(run, 'artifacts', 'artifacts') if not item['expired']}
    if not states:
        raise ValueError('No successful state builds found')
    for state in states:
        if f'us-coarse-terrain-{state}-{run}' not in available:
            raise ValueError(f'{state}: artifact unavailable or expired')
    output.mkdir(parents=True, exist_ok=True)
    failed = []
    for number, state in enumerate(states, 1):
        print(f'\nState {number}/{len(states)}: {state}', flush=True)
        try:
            fetch_state(run, state, output, reuse, attempts=attempts)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, ValueError) as error:
            failed.append(state)
            print(f'{state}: not completed ({type(error).__name__}); continuing', flush=True)
    report = dict(run=str(run), successful_source_states=states, failed_downloads=failed,
                  note='Completed states are checksum verified; no terrain has been activated')
    (output/'download-report.json').write_text(json.dumps(report, indent=2))
    print(f'\nVerified {len(states)-len(failed)}/{len(states)} states. Re-run to finish missing transfers.')
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', default='44150040908')
    parser.add_argument('--directory', type=Path, default=Path('build-output/us-terrain'))
    parser.add_argument('--reuse-directory', type=Path, action='append', default=[])
    parser.add_argument('--attempts', type=int, default=3)
    args = parser.parse_args()
    try:
        return download(args.run, args.directory, args.reuse_directory, attempts=args.attempts)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f'US terrain download failed: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
