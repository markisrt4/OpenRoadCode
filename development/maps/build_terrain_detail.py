"""Build bounded 10 m-class terrain detail from existing staged USGS 3DEP rasters."""
import argparse
import json
import math
from pathlib import Path
import time

from apps.launchers.local_terrain_pack import load_terrain
from development.maps.detail_coverages import TERRAIN_DETAILS
from development.maps.static_region_build import source_crops, terrain_pack
from development.maps.static_region_sources import discover_terrain
from development.maps.static_tile_trial import write_json
from tools.map_builder.builder.terrain_artifact import package


def grid_definition(bounds,spacing_m=10):
    w,s,e,n=bounds
    width=(e-w)*111320*math.cos(math.radians((s+n)/2))
    height=(n-s)*111320
    divisions=max(1,math.ceil(max(width,height)/(128*spacing_m)))
    if divisions>8:
        raise ValueError('Detail coverage too large for bounded 64-tile terrain pack')
    return divisions,dict(longitude_m=width/(128*divisions),latitude_m=height/(128*divisions))


def build(output,cache,coverage):
    output.mkdir(parents=True,exist_ok=True);cache.mkdir(parents=True,exist_ok=True)
    title,bounds=TERRAIN_DETAILS[coverage]
    started=time.monotonic()
    report=dict(status='started',coverage=coverage,bounds_deg=bounds)
    try:
        divisions,spacing=grid_definition(bounds)
        size=divisions*128+1
        w,s,e,n=bounds;dx,dy=(e-w)/(size-1),(n-s)/(size-1)
        source_bounds=(w-dx/2,s-dy/2,e+dx/2,n+dy/2)
        path=cache/'source-plan.json'
        plan=json.loads(path.read_text()) if path.is_file() else {}
        if plan.get("plan_revision")==2:
            if plan.get('coverage')!=coverage or plan.get('bounds_deg')!=list(bounds):
                raise ValueError('Cached terrain detail plan coverage mismatch')
        else:
            plan=dict(coverage=coverage,bounds_deg=bounds,plan_revision=2,terrain=discover_terrain(source_bounds))
            write_json(path,plan)
        # One extra sample aligns endpoint centers; crop dimensions are part of
        # the existing cache key. Sources remain public staged files, not exports.
        crops,receipts=source_crops(plan['terrain'],cache/'crops',source_bounds,size,'terrain')
        pack,metrics=terrain_pack(output,coverage,plan['terrain'],crops,bounds=bounds,title=title,divisions=divisions)
        manifest=json.loads((pack/'manifest.json').read_text())
        for tile in manifest['tiles']:
            tile.update(detail_level=5,minimum_zoom=13)
        manifest.update(maximum_zoom=16,source_product='USGS 3DEP 1/3 arc-second (~10 m)',
                        sample_spacing_m=spacing,build_profile='staged-3dep-10m-class-v1')
        write_json(pack/'manifest.json',manifest)
        write_json(pack/'source-plan.json',plan);write_json(pack/'source-receipts.json',receipts)
        load_terrain(pack)
        descriptor=package(pack,output/(coverage+'-terrain.zip'),coverage)
        report.update(metrics,status='validated',sample_spacing_m=spacing,maximum_terrain_zoom=16,
                      source_product=manifest['source_product'],archive_bytes=descriptor['bytes'],
                      source_dates=sorted({item['date'] for item in plan['terrain']}),
                      source_date_note='Catalog update/publication dates; not established survey acquisition dates',
                      source_urls=[item['url'] for item in plan['terrain']])
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,2)
        write_json(output/'terrain-detail-report.json',report)
        print('Terrain detail report: '+json.dumps(report,sort_keys=True),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage',choices=tuple(TERRAIN_DETAILS),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    args=parser.parse_args();build(args.output,args.cache,args.coverage)


if __name__=='__main__':main()
