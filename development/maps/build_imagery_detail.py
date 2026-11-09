"""Build native offline zoom tiles for two bounded NAIP detail pilots."""

import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import time
import zipfile

from apps.launchers.local_imagery_pyramid import LocalImageryPyramidPack, PILOT_BOUNDS
from development.maps.static_region_build import source_crops
from development.maps.static_region_sources import discover_imagery
from development.maps.static_tile_trial import RIGHTS, command, digest, write_json

MAX_ARCHIVE_BYTES = 512*1024*1024
MINIMUM_ZOOM = 10
MAXIMUM_ZOOM = 16


def raster_to_pyramid(crops, output, coverage):
    """Reuse aligned source crops; GDAL generates standard Web Mercator MBTiles."""
    bounds = PILOT_BOUNDS[coverage]
    scratch = output/'processing'
    scratch.mkdir(parents=True, exist_ok=True)
    listing = scratch/'sources.txt'
    listing.write_text('\n'.join(str(path.resolve()) for path in crops)+'\n')
    vrt = scratch/'sources.vrt'
    command('gdalbuildvrt','-overwrite','-input_file_list',listing,vrt)
    pack = output/'pack'
    pack.mkdir(exist_ok=True)
    database = pack/'imagery.mbtiles'
    database.unlink(missing_ok=True)
    resolution = 2*math.pi*6378137/(256*2**MAXIMUM_ZOOM)
    command('gdalwarp','-overwrite','-wm','128','-t_srs','EPSG:3857',
            '-tr',resolution,resolution,'-tap','-r','bilinear','-srcalpha','-dstalpha',
            '-of','MBTiles','-co','TILE_FORMAT=WEBP','-co','QUALITY=88',vrt,database)
    factors = [2**index for index in range(1,MAXIMUM_ZOOM-MINIMUM_ZOOM+1)]
    command('gdaladdo','-r','average',database,*factors)
    with closing(sqlite3.connect(database)) as connection:
        count, low, high = connection.execute('SELECT count(*),min(zoom_level),max(zoom_level) FROM tiles').fetchone()
        metadata = dict(connection.execute('SELECT name,value FROM metadata'))
        if (low,high) != (MINIMUM_ZOOM,MAXIMUM_ZOOM):
            raise ValueError(f'Unexpected GDAL zoom coverage: {low}–{high}')
        for key,value in dict(minzoom=str(low),maxzoom=str(high)).items():
            connection.execute('DELETE FROM metadata WHERE name=?',(key,))
            connection.execute('INSERT INTO metadata(name,value) VALUES(?,?)',(key,value))
        connection.commit()
    write_json(pack/'manifest.json',dict(schema=1,kind='imagery-pyramid',coverage=coverage,
        database=database.name,sha256=digest(database),bounds_deg=bounds,
        title=coverage.replace('-',' ').title()+' NAIP detail',attribution='USDA NAIP / USGS · The National Map',
        rights='Public-domain USDA NAIP',rights_reference=RIGHTS['imagery'],
        native_zoom=high,ground_pixel_spacing_m_at_center=resolution*math.cos(math.radians((bounds[1]+bounds[3])/2)),
        note='Native source resolution/date vary; transparent pixels are unfilled source gaps'))
    LocalImageryPyramidPack.load(pack)
    return pack,dict(tile_count=count,minimum_zoom=low,maximum_zoom=high,image_format=metadata['format'],
                     database_bytes=database.stat().st_size,
                     target_ground_pixel_spacing_m=resolution*math.cos(math.radians((bounds[1]+bounds[3])/2)))


def package(pack, output, coverage):
    LocalImageryPyramidPack.load(pack)
    archive = output/(coverage+'-imagery-detail.zip')
    temporary = archive.with_suffix('.zip.part')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(pack.iterdir()):
                if not path.is_file() or path.is_symlink():
                    raise ValueError('Unexpected imagery detail artifact layout')
                zipped.write(path,path.name)
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError('Imagery detail archive exceeds 512 MiB')
        temporary.replace(archive)
        descriptor = dict(schema=1,kind='imagery-pyramid',coverage=coverage,archive=archive.name,
            bytes=archive.stat().st_size,sha256=digest(archive),bounds_deg=PILOT_BOUNDS[coverage],
            build_profile='naip-web-mercator-z10-z16-256px',build_revision='imagery-pyramid-v1')
        write_json(archive.with_suffix('.zip.json'),descriptor)
        return descriptor
    finally:
        temporary.unlink(missing_ok=True)


def build(output, cache, coverage):
    output.mkdir(parents=True,exist_ok=True)
    cache.mkdir(parents=True,exist_ok=True)
    started = time.monotonic()
    report = dict(status='started',coverage=coverage,bounds_deg=PILOT_BOUNDS[coverage])
    try:
        plan_path = cache/'source-plan.json'
        if plan_path.is_file():
            plan = json.loads(plan_path.read_text())
            if plan.get('coverage') != coverage or plan.get('bounds_deg') != list(PILOT_BOUNDS[coverage]):
                raise ValueError('Cached imagery detail source plan coverage mismatch')
        else:
            plan = dict(coverage=coverage,bounds_deg=PILOT_BOUNDS[coverage],rights=RIGHTS['imagery'],
                        imagery=discover_imagery(PILOT_BOUNDS[coverage]))
            write_json(plan_path,plan)
        # Preserve source detail before reducing into 256px zoom tiles. Source crops
        # never become whole-region browser textures.
        crops,receipts = source_crops(plan['imagery'],cache/'crops',PILOT_BOUNDS[coverage],4096,'imagery')
        pack,metrics = raster_to_pyramid(crops,output,coverage)
        write_json(pack/'source-plan.json',plan)
        write_json(pack/'source-receipts.json',receipts)
        descriptor = package(pack,output,coverage)
        report.update(metrics,status='validated',archive_bytes=descriptor['bytes'],
                      source_count=len(plan['imagery']),
                      source_dates=sorted({item['date'][:10] for item in plan['imagery']}),
                      network_transfer_bytes=None)
    except Exception as error:
        report.update(status='failed',error=str(error))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic()-started,2)
        write_json(output/'detail-report.json',report)
        print('Imagery detail report: '+json.dumps(report,sort_keys=True),flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coverage',choices=tuple(PILOT_BOUNDS),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    args = parser.parse_args()
    build(args.output,args.cache,args.coverage)


if __name__ == '__main__':
    main()
