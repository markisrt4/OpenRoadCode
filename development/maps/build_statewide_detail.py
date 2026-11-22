"""Build three bounded Michigan detail delivery cells per Actions worker."""
import argparse
import json
from pathlib import Path
import shutil
import time
import zipfile

from apps.launchers.local_imagery_pyramid import LocalImageryPyramidPack
from apps.launchers.local_terrain_pack import load_terrain
from development.maps.build_imagery_detail import raster_to_pyramid
from development.maps.build_terrain_detail import grid_definition
from development.maps.statewide_detail_plan import PROFILE,IMAGE_ZOOM,MAX_CELL_ARCHIVE
from development.maps.static_region_build import source_crops,terrain_pack
from development.maps.static_region_sources import discover_imagery,discover_terrain
from development.maps.static_tile_trial import digest,write_json



def optional_sources(discover,bounds,empty_message):
    try:return discover(bounds)
    except ValueError as error:
        if str(error).startswith(empty_message):return []
        raise


def build_cell(cell,output):
    key=cell['id'];bounds=cell['bounds_deg'];directory=output/key
    directory.mkdir(parents=True,exist_ok=True)
    pack=directory/'pack';pack.mkdir()
    started=time.monotonic()
    report=dict(id=key,bounds_deg=bounds,profile=PROFILE,status='started')
    try:
        imagery=optional_sources(discover_imagery,bounds,'No dated NAIP files')
        if imagery:
            crops,receipts=source_crops(imagery,directory/'image-crops',bounds,16384,'imagery')
            root,metrics=raster_to_pyramid(crops,directory/'image',key,maximum_zoom=IMAGE_ZOOM,bounds=bounds)
            write_json(root/'source-records.json',imagery);write_json(root/'source-receipts.json',receipts)
            shutil.move(root,pack/'imagery');report['imagery']=metrics
        divisions,spacing=grid_definition(bounds,30)
        size=divisions*128+1;w,s,e,n=bounds;dx,dy=(e-w)/(size-1),(n-s)/(size-1)
        crop_bounds=(w-dx/2,s-dy/2,e+dx/2,n+dy/2)
        terrain=optional_sources(discover_terrain,crop_bounds,'No staged 3DEP files')
        if terrain:
            crops,receipts=source_crops(terrain,directory/'terrain-crops',crop_bounds,size,'terrain')
            try:
                root,metrics=terrain_pack(directory/'dem',key,terrain,crops,bounds=bounds,title=key,divisions=divisions)
            except ValueError as error:
                if not str(error).startswith('No complete regional terrain tiles'):raise
                report['terrain_gap']=str(error)
            else:
                manifest=json.loads((root/'manifest.json').read_text())
                for tile in manifest['tiles']:tile.update(detail_level=5,minimum_zoom=12)
                write_json(root/'manifest.json',manifest);write_json(root/'source-receipts.json',receipts)
                load_terrain(root);shutil.move(root,pack/'terrain')
                report['terrain']={**metrics,'sample_spacing_m':spacing}
        if (pack/'imagery').is_dir():LocalImageryPyramidPack.load(pack/'imagery')
        report.update(status='validated',imagery_available=(pack/'imagery').is_dir(),
                      terrain_available=(pack/'terrain').is_dir(),
                      imagery_dates=sorted({item['date'][:10] for item in imagery}),
                      terrain_record_dates=sorted({item['date'] for item in terrain}),
                      note='Record dates are not established terrain survey dates; gaps use installed coarse data')
        write_json(pack/'manifest.json',{**cell,**report,'schema':1,'kind':'michigan-detail-cell'})
        archive=output/(key+'.zip');temporary=archive.with_suffix('.zip.part')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(pack.rglob('*')):
                if path.is_file():zipped.write(path,path.relative_to(pack).as_posix())
        if temporary.stat().st_size>MAX_CELL_ARCHIVE:raise ValueError('Detail cell archive exceeds 600 MiB')
        temporary.replace(archive)
        descriptor=dict(schema=1,kind='michigan-detail-cell',coverage=key,profile=PROFILE,archive=archive.name,
                        bytes=archive.stat().st_size,sha256=digest(archive),bounds_deg=bounds,
                        unpacked_bytes=sum(p.stat().st_size for p in pack.rglob('*') if p.is_file()))
        write_json(archive.with_suffix('.zip.json'),descriptor)
        report.update(archive_bytes=descriptor['bytes'],unpacked_bytes=descriptor['unpacked_bytes'])
        return report
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,2)
        write_json(output/(key+'-report.json'),report)
        shutil.rmtree(directory,ignore_errors=True)


def batch(plan,batch_id,output):
    output.mkdir(parents=True,exist_ok=True)
    selected=next(b for b in plan['batches'] if b['id']==batch_id)
    reports=[];errors=[]
    for index,cell in enumerate(selected['cells'],1):
        print(f"Detail cell {index}/{len(selected['cells'])}: {cell['id']}",flush=True)
        archive=output/(cell['id']+'.zip');descriptor=archive.with_suffix('.zip.json')
        if archive.is_file() and descriptor.is_file():
            saved=json.loads(descriptor.read_text())
            if (saved.get('profile')==PROFILE and saved.get('coverage')==cell['id']
                    and saved.get('bounds_deg')==cell['bounds_deg'] and saved.get('bytes')==archive.stat().st_size
                    and saved.get('sha256')==digest(archive)):
                print('Reusing verified completed cell',flush=True);continue
        try:reports.append(build_cell(cell,output))
        except Exception as error:
            errors.append(dict(id=cell['id'],error=str(error)));print(f"Cell failed: {cell['id']}: {error}",flush=True)
    write_json(output/'batch-report.json',dict(batch=batch_id,reports=reports,errors=errors))
    if errors:raise RuntimeError(f'{len(errors)} detail cells failed; completed archives retained')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--batch',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();batch(json.loads(args.plan.read_text()),args.batch,args.output)


if __name__=='__main__':main()
