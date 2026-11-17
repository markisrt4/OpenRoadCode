"""Plan missing batches using small receipts and live artifact references only."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from development.maps.statewide_detail_plan import PROFILE


def artifacts(run):
    pages = json.loads(subprocess.check_output([
        'gh', 'api', '--paginate', '--slurp',
        f'repos/markisrt4/OpenRoadCode/actions/runs/{run}/artifacts?per_page=100'], text=True))
    return {(str(run), item['name']) for page in pages for item in page['artifacts']
            if not item['expired'] and item['size_in_bytes'] > 0}


def resume(plan, directory, live, inherited=None):
    expected = {cell['id']: cell for cell in plan['cells']}
    rows = {}
    candidates = list((inherited or {}).get('cells', {}).values())
    for path in Path(directory).rglob('*.zip.json'):
        match = next((re.fullmatch(r'mi-detail-reports-(\d+)-(\d+)', parent.name)
                      for parent in path.parents if re.fullmatch(r'mi-detail-reports-(\d+)-(\d+)', parent.name)), None)
        if match:
            batch, run = match.groups()
            candidates.append(dict(run_id=run, artifact=f'mi-detail-batch-{batch}-{run}',
                                   descriptor=json.loads(path.read_text())))
    for row in candidates:
        descriptor = row['descriptor']; key = descriptor.get('coverage')
        if key not in expected or descriptor.get('profile') != PROFILE:
            raise ValueError('Unexpected resume descriptor')
        if (descriptor.get('bounds_deg') != expected[key]['bounds_deg']
                or not re.fullmatch('[0-9a-f]{64}', descriptor.get('sha256', ''))
                or type(descriptor.get('bytes')) is not int or descriptor['bytes'] <= 0):
            raise ValueError('Invalid resume receipt')
        if (str(row['run_id']), row['artifact']) not in live:
            continue
        if key in rows and rows[key]['descriptor'] != descriptor:
            raise ValueError('Conflicting resume receipts')
        rows[key] = row
    missing = [batch['id'] for batch in plan['batches']
               if any(cell['id'] not in rows for cell in batch['cells'])]
    return dict(schema=1, profile=PROFILE, cells=rows, missing_batches=missing,
                note='Artifact references; archive checksums are verified at installation, not downloaded during planning')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inherited', type=Path)
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args()
    inherited = json.loads(args.inherited.read_text()) if args.inherited and args.inherited.is_file() else None
    runs = {args.run} | {str(row['run_id']) for row in (inherited or {}).get('cells', {}).values()}
    live = set().union(*(artifacts(run) for run in runs))
    result = resume(json.loads(args.plan.read_text()), args.directory, live, inherited)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    if args.github_output:
        with args.github_output.open('a') as stream:
            stream.write('matrix='+json.dumps(result['missing_batches'])+'\n')
            stream.write('has_work='+str(bool(result['missing_batches'])).lower()+'\n')
    print(f"Reusing {len(result['cells'])} cell references; scheduling {len(result['missing_batches'])} batches")


if __name__ == '__main__':
    main()
