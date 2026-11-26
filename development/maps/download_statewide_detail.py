"""Resolve a delivery's artifact references without downloading duplicate batches."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from development.maps.statewide_detail_plan import PROFILE, parse_cell
from development.maps.static_tile_trial import digest


def download(delivery, output):
    if delivery.get('profile') != PROFILE:
        raise ValueError('Wrong statewide delivery profile')
    output.mkdir(parents=True, exist_ok=True)
    groups = {}
    for key, row in delivery['cells'].items():
        parse_cell(key)
        if not str(row['run_id']).isdigit():
            raise ValueError('Invalid artifact run')
        groups.setdefault((str(row['run_id']), row['artifact']), []).append((key, row['descriptor']))
    for index, ((run, artifact), rows) in enumerate(groups.items(), 1):
        missing = [(key, descriptor) for key, descriptor in rows
                   if not (output/(key+'.zip')).is_file()
                   or (output/(key+'.zip')).stat().st_size != descriptor['bytes']
                   or digest(output/(key+'.zip')) != descriptor['sha256']
                   or not (output/(key+'.zip.json')).is_file()]
        if not missing:
            continue
        print(f'Download batch {index}/{len(groups)} · run {run}', flush=True)
        with TemporaryDirectory(dir=output) as temporary:
            subprocess.run(['gh', 'run', 'download', run, '--repo', 'markisrt4/OpenRoadCode',
                            '--name', artifact, '--dir', temporary], check=True)
            for key, descriptor in missing:
                archive = Path(temporary)/(key+'.zip')
                if archive.stat().st_size != descriptor['bytes'] or digest(archive) != descriptor['sha256']:
                    raise ValueError('Downloaded cell does not match delivery checksum')
                shutil.move(archive, output/archive.name)
                (output/(key+'.zip.json')).write_text(json.dumps(descriptor))
    print('Cell archives verified. Install with install_statewide_detail and the matching plan artifact.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--delivery', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    download(json.loads(args.delivery.read_text()), args.output)


if __name__ == '__main__':
    main()
