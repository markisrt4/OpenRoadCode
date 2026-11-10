"""Summarize statewide completeness using small descriptors, not full raster ZIPs."""
import argparse
import json
from pathlib import Path

from development.maps.statewide_detail_plan import PROFILE


def summarize(plan,directory):
    expected={c['id'] for c in plan['cells']};found={}
    for path in Path(directory).rglob('*.zip.json'):
        descriptor=json.loads(path.read_text());key=descriptor.get('coverage')
        if descriptor.get('profile')!=PROFILE or key not in expected:raise ValueError('Unexpected detail descriptor')
        if key in found and found[key]!=descriptor:raise ValueError('Conflicting detail descriptor revisions')
        found[key]=descriptor
    gaps=[]
    for path in Path(directory).rglob('*-report.json'):
        report=json.loads(path.read_text())
        if report.get('profile')!=PROFILE or report.get('id') not in expected:continue
        missing=report.get('terrain',{}).get('missing_terrain_tiles',[])
        if missing or not report.get('imagery_available') or not report.get('terrain_available'):
            gaps.append(dict(id=report['id'],imagery_available=report.get('imagery_available'),
                             terrain_available=report.get('terrain_available'),missing_terrain_tiles=len(missing)))
    absent=sorted(expected-set(found))
    return dict(schema=1,profile=PROFILE,complete=not absent,delivery_complete=not absent,source_coverage_not_certified=True,cells=len(found),planned_cells=len(expected),
                missing_cells=absent,archive_bytes=sum(d['bytes'] for d in found.values()),
                unpacked_bytes=sum(d.get('unpacked_bytes',0) for d in found.values()),source_gaps=gaps)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=summarize(json.loads(args.plan.read_text()),args.directory)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2))
    print('Statewide detail summary: '+json.dumps(report,sort_keys=True),flush=True)
    if not report['complete']:raise SystemExit('Statewide detail is incomplete; retry failed batches')


if __name__=='__main__':main()
