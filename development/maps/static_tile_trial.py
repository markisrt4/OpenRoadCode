"""Experimental Rochester pack build from staged NAIP/3DEP files, not exports.

GDAL is required on the build host only. Never installs or activates phone data.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, quote
from urllib.request import urlopen

from PIL import Image
from apps.launchers.local_imagery_pack import LocalImageryPack
from apps.launchers.local_terrain_pack import load_terrain
from development.maps.download_detroit_imagery import SERVICE, CATALOG_FIELDS
from tools.map_builder.builder.map_3d import PRESETS
from tools.map_builder.builder.imagery_artifact import package as package_imagery
from tools.map_builder.builder.terrain_artifact import package as package_terrain

BOUNDS = PRESETS['rochester'][1]
TNM = 'https://tnmaccess.nationalmap.gov/api/v1/products'
PC = 'https://planetarycomputer.microsoft.com/api'
MAX_SOURCE_BYTES = 1024 * 1024 * 1024
MAX_FILE_BYTES = 512 * 1024 * 1024
RIGHTS = {
    'imagery': 'https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip',
    'terrain': 'https://www.usgs.gov/3d-elevation-program/about-3dep-products-services',
}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2))


def get_json(url, **parameters):
    print(f'Catalog: {url}',flush=True)
    address=url+('?' + urlencode(parameters) if parameters else '')
    for attempt in range(3):
        try:
            with urlopen(address,timeout=30) as response:
                raw=response.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:raise ValueError('Catalog exceeds trial limit')
            data=json.loads(raw)
            if isinstance(data,dict) and data.get('error'):raise ValueError(f'Catalog error: {data["error"]}')
            return data
        except (URLError,TimeoutError):
            if attempt==2:raise
            time.sleep(2**attempt)


def approved_url(url):
    parsed=urlsplit(url)
    staged=parsed.hostname=='prd-tnm.s3.amazonaws.com' and parsed.path.startswith('/StagedProducts/')
    mirror=parsed.hostname=='naipeuwest.blob.core.windows.net' and parsed.path.startswith('/naip/')
    if parsed.scheme!='https' or not (staged or mirror) or parsed.query or parsed.fragment:
        raise ValueError(f'Source is not an approved staged NAIP/3DEP file: {parsed.hostname}{parsed.path}')
    return url


def staged_imagery_url(record):
    url=record['download_url']
    if urlsplit(url).hostname=='prd-tnm.s3.amazonaws.com':return approved_url(url)
    if urlsplit(url).hostname!='earthexplorer.usgs.gov':return approved_url(url)
    stems={Path(str(record.get(key) or '')).stem for key in ('Name','raster_name')}
    stems={stem for stem in stems if re.fullmatch(r'm_[0-9]{7}_[a-z0-9_]+',stem.lower())}
    if not stems:raise ValueError('NAIP catalog lacks a recognizable staged raster name')
    cells={stem[2:7] for stem in stems}
    if len(cells)!=1:raise ValueError('NAIP catalog raster names disagree on grid cell')
    prefix=f'StagedProducts/NAIP/mi_{record["Year"]}/{next(iter(cells))}/'
    address='https://prd-tnm.s3.amazonaws.com/?'+urlencode({'list-type':2,'prefix':prefix,'max-keys':1000})
    print(f'Staged NAIP directory: {prefix}',flush=True)
    with urlopen(address,timeout=60) as response:
        raw=response.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise ValueError('Staged directory exceeds trial limit')
    document=ET.fromstring(raw)
    if document.findtext('{*}IsTruncated')=='true':raise ValueError('Staged NAIP directory is truncated')
    matches=[]
    for entry in document.findall('{*}Contents'):
        key=entry.findtext('{*}Key') or ''
        path=Path(key)
        if key.startswith(prefix) and path.suffix.lower() in ('.jp2','.tif') and any(
                path.stem==stem or path.stem.startswith(stem+'_') for stem in stems):
            matches.append(key)
    if not matches:
        state_prefix=f'StagedProducts/NAIP/mi_{record["Year"]}/'
        address='https://prd-tnm.s3.amazonaws.com/?'+urlencode({'list-type':2,'prefix':state_prefix,'delimiter':'/','max-keys':1000})
        with urlopen(address,timeout=60) as response:
            listing=ET.fromstring(response.read(2*1024*1024))
        folders=[item.findtext('{*}Prefix') for item in listing.findall('{*}CommonPrefixes')]
        keys=[item.findtext('{*}Key') for item in document.findall('{*}Contents')]
        raise ValueError(f'No matching staged NAIP file for catalog names {sorted(stems)}; directory keys={keys[:8]}; state folders={folders[:12]}')
    chosen=sorted(matches,key=lambda key:(Path(key).suffix.lower()=='.jp2',key))[-1]
    return approved_url('https://prd-tnm.s3.amazonaws.com/'+quote(chosen,safe='/'))


def select_imagery(catalog):
    if catalog.get('exceededTransferLimit'):raise ValueError('Trial catalog is incomplete')
    records=[feature['attributes'] for feature in catalog.get('features',[])]
    records=[r for r in records if isinstance(r.get('Year'),int)
             and 'naip' in (str(r.get('Name',''))+' '+str(r.get('download_url',''))).lower()]
    if not records:raise ValueError('No dated staged NAIP products found')
    year=max(r['Year'] for r in records)
    selected={staged_imagery_url(r):r for r in records if r['Year']==year and r.get('download_url')}
    if not selected or len(selected)>12:raise ValueError('Trial requires 1–12 dated NAIP files')
    return [{'url':url,'record':record} for url,record in sorted(selected.items())]


def select_dem(catalog):
    west,south,east,north=BOUNDS
    candidates=[]
    for item in catalog.get('items',[]):
        box=item.get('boundingBox',{})
        if (box.get('minX',180)<=west and box.get('minY',90)<=south
                and box.get('maxX',-180)>=east and box.get('maxY',-90)>=north):
            url=item.get('downloadURL','')
            if url.lower().endswith('.tif'):
                candidates.append({'url':approved_url(url),'record':item})
    if not candidates:raise ValueError('No staged DEM covering Rochester; source review required')
    return max(candidates,key=lambda item:str(item['record'].get('lastUpdated') or item['record'].get('publicationDate') or ''))


def planetary_imagery():
    collection=get_json(PC+'/stac/v1/collections/naip')
    if not any('USDA' in provider.get('name','') and 'licensor' in provider.get('roles',[])
               for provider in collection.get('providers',[])):
        raise ValueError('Mirror NAIP collection no longer identifies USDA as licensor')
    catalog=get_json(PC+'/stac/v1/search',collections='naip',bbox=','.join(map(str,BOUNDS)),limit=100)
    if any(link.get('rel')=='next' for link in catalog.get('links',[])):
        raise ValueError('Mirror catalog is incomplete within trial limits')
    items=catalog.get('features',[])
    if not items:raise ValueError('No NAIP mirror imagery in Rochester')
    dated=[]
    for item in items:
        if item.get('collection')!='naip':raise ValueError('Unexpected mirror imagery collection')
        date=item.get('properties',{}).get('datetime') or item.get('properties',{}).get('start_datetime') or ''
        if not re.match(r'^20[0-9]{2}-',date):raise ValueError('Undated mirror NAIP item')
        dated.append((int(date[:4]),item))
    year=max(value[0] for value in dated)
    selected=[]
    for date,item in dated:
        if date!=year:continue
        asset=item['assets']['image']
        url=approved_url(asset['href'])
        if urlsplit(url).hostname!='naipeuwest.blob.core.windows.net':raise ValueError('Unexpected mirror storage')
        selected.append({'url':url,'record':item})
    selected=list({item['url']:item for item in selected}.values())
    if not 1<=len(selected)<=12:raise ValueError('Mirror trial requires 1–12 NAIP files')
    print(f'Mirror NAIP: {year} · {len(selected)} staged files',flush=True)
    return selected,{'collection':collection,'catalog':catalog}


def source_request_url(url):
    if urlsplit(url).hostname!='naipeuwest.blob.core.windows.net':return url
    signed=get_json(PC+'/sas/v1/sign',href=url)['href']
    if urlunsplit(urlsplit(signed)._replace(query='',fragment=''))!=url:
        raise ValueError('Mirror signing endpoint changed the requested file')
    return signed


def discover(output=None, imagery_source="usgs"):
    if imagery_source=='planetary-computer':
        selected,imagery=planetary_imagery()
        metadata={'delivery':'Microsoft Planetary Computer public NAIP mirror','rights':RIGHTS['imagery'],
                  'access_reference':'https://planetarycomputer.microsoft.com/docs/concepts/sas/'}
    else:
        metadata=get_json(SERVICE,f='json')
        if 'public domain' not in metadata.get('serviceDescription','').lower():
            raise ValueError('NAIP service no longer declares public-domain source data')
        imagery=get_json(SERVICE+'/query',f='json',where="State='MI' AND Category=1",
                         geometry=','.join(map(str,BOUNDS)),geometryType='esriGeometryEnvelope',
                         inSR=4326,spatialRel='esriSpatialRelIntersects',returnGeometry='false',outFields=CATALOG_FIELDS)
        selected=None
    terrain=get_json(TNM,bbox=','.join(map(str,BOUNDS)),
                     datasets='National Elevation Dataset (NED) 1/3 arc-second',max=100,outputFormat='JSON')
    if output is not None:
        write_json(output/'source-plan.json',{'source_catalogs':{'imagery':imagery,'terrain':terrain,'imagery_service':metadata}})
    return {'coverage':'rochester','bounds_deg':BOUNDS,'rights':RIGHTS,
            'discovered_at':datetime.now(timezone.utc).isoformat(),
            'imagery':selected if selected is not None else select_imagery(imagery),'terrain':[select_dem(terrain)],
            'source_catalogs':{'imagery':imagery,'terrain':terrain,'imagery_service':metadata}}


def download_source(url, cache, remaining):
    approved_url(url)
    print(f'Staged source: {url}',flush=True)
    key=hashlib.sha256(url.encode()).hexdigest()
    target=cache/(key+Path(urlsplit(url).path).suffix)
    receipt=cache/(key+'.json')
    if target.is_file() and receipt.is_file():
        saved=json.loads(receipt.read_text())
        if (target.stat().st_size<=min(remaining,MAX_FILE_BYTES) and saved['url']==url
                and saved['sha256']==digest(target)):
            return target,saved
    temporary=target.with_suffix(target.suffix+'.part')
    for attempt in range(3):
        count=0
        try:
            with urlopen(source_request_url(url),timeout=60) as response,temporary.open('wb') as output:
                actual=urlunsplit(urlsplit(response.geturl())._replace(query='',fragment=''))
                if approved_url(actual)!=url:raise ValueError('Staged source redirected to another file')
                expected=int(response.headers.get('Content-Length',0))
                if expected>min(remaining,MAX_FILE_BYTES):raise ValueError('Source exceeds trial transfer cap')
                while chunk:=response.read(1024*1024):
                    count+=len(chunk)
                    if count>min(remaining,MAX_FILE_BYTES):raise ValueError('Source exceeds trial transfer cap')
                    output.write(chunk)
                if not count or (expected and count!=expected):raise ValueError('Incomplete staged source file')
                output.flush()
                saved={'url':url,'bytes':count,'sha256':digest(temporary),
                       'etag':response.headers.get('ETag'),'last_modified':response.headers.get('Last-Modified'),
                       'downloaded_at':datetime.now(timezone.utc).isoformat()}
            temporary.replace(target)
            write_json(receipt,saved)
            return target,saved
        except (URLError,TimeoutError) as error:
            if attempt==2:raise
            if isinstance(error,HTTPError) and error.code not in (429,500,502,503,504):raise
            time.sleep(2**attempt)
        finally:temporary.unlink(missing_ok=True)


def redact(text):
    return re.sub(r'(https://[^\s?]+)\?[^\s]+',r'\1?[redacted]',str(text))


def command(*args):
    print('GDAL:',*[redact(arg) for arg in args],flush=True)
    try:
        result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=600)
    except subprocess.TimeoutExpired:
        raise RuntimeError('GDAL trial processing timed out') from None
    if result.returncode:
        raise RuntimeError('GDAL failed: '+redact(result.stderr[-3000:]))
    return result.stdout


def crop_cog(url, cache, remaining):
    """Read only the required COG blocks and cache a self-contained local crop."""
    approved_url(url)
    key=hashlib.sha256((url+str(BOUNDS)+'crop-v1').encode()).hexdigest()
    target=cache/(key+'.tif');receipt=cache/(key+'.json')
    if target.is_file() and receipt.is_file():
        saved=json.loads(receipt.read_text())
        if saved['url']==url and target.stat().st_size<=remaining and saved['sha256']==digest(target):
            return target,saved
    temporary=cache/(key+'.part.tif')
    try:
        signed=source_request_url(url)
        command('gdalwarp','-overwrite','-wm','128','-t_srs','EPSG:4326','-te',*BOUNDS,
                '-ts','4096','4096','-r','bilinear','-srcband','1','-srcband','2','-srcband','3',
                '-dstalpha','-co','COMPRESS=DEFLATE','/vsicurl/'+signed,temporary)
        if temporary.stat().st_size>min(remaining,MAX_FILE_BYTES):raise ValueError('COG crop exceeds trial cache cap')
        saved={'url':url,'bytes':temporary.stat().st_size,'sha256':digest(temporary),
               'method':'COG HTTP range crop; bytes measure cached crop, not network transfer',
               'bounds_deg':BOUNDS,'downloaded_at':datetime.now(timezone.utc).isoformat()}
        temporary.replace(target);write_json(receipt,saved)
        return target,saved
    finally:temporary.unlink(missing_ok=True)


def process(plan, files, output):
    west,south,east,north=BOUNDS
    bounds=tuple(map(str,BOUNDS))
    dx,dy=(east-west)/128,(north-south)/128
    sample_bounds=tuple(map(str,(west-dx/2,south-dy/2,east+dx/2,north+dy/2)))
    scratch=output/'processing'
    scratch.mkdir(parents=True,exist_ok=True)
    images=[];alpha_inputs=[]
    for index,source in enumerate(files['imagery']):
        vrt=scratch/f'rgb-{index}.vrt'
        info=json.loads(command('gdalinfo','-json',source))
        alpha=[band['band'] for band in info['bands'] if band.get('colorInterpretation')=='Alpha']
        alpha_inputs.append(bool(alpha))
        bands=[str(index) for index in [1,2,3]+alpha]
        arguments=[value for band in bands for value in ('-b',band)]
        command('gdal_translate','-of','VRT',*arguments,source,vrt)
        images.append(vrt)
    if any(alpha_inputs) and not all(alpha_inputs):raise ValueError('Mixed alpha and RGB source layouts need review')
    source_alpha=('-srcalpha',) if all(alpha_inputs) else ()
    mosaic=scratch/'imagery.tif'
    command('gdalwarp','-overwrite','-wm','128','-t_srs','EPSG:4326','-te',*bounds,
            '-ts','4096','4096','-r','bilinear',*source_alpha,'-dstalpha','-of','GTiff',*images,mosaic)
    imagery=output/'rochester-imagery'
    imagery.mkdir(exist_ok=True)
    with Image.open(mosaic) as image:
        image.load()
        if image.getchannel('A').getextrema()!=(255,255):
            raise ValueError('Source imagery does not cover the complete trial area; no pack published')
        with image.convert('RGB') as rgb:rgb.save(imagery/'imagery.jpg',quality=90,optimize=True)
    write_json(imagery/'manifest.json',{'schema':1,'image':'imagery.jpg','sha256':digest(imagery/'imagery.jpg'),
        'title':'Rochester staged NAIP trial','attribution':'USDA NAIP / USGS · The National Map',
        'bounds_deg':BOUNDS,'width':4096,'height':4096,'source_records':plan['imagery'],
        'rights':'Public-domain USDA NAIP imagery','rights_reference':RIGHTS['imagery']})
    grid=scratch/'terrain.tif'
    command('gdalwarp','-overwrite','-wm','128','-t_srs','EPSG:4326','-te',*sample_bounds,
            '-ts','129','129','-r','bilinear','-dstnodata','-9999',files['terrain'][0],grid)
    xyz=scratch/'terrain.xyz'
    command('gdal_translate','-of','XYZ',grid,xyz)
    heights=[float(line.split()[2]) for line in xyz.read_text().splitlines()]
    if len(heights)!=129*129 or any(not math.isfinite(h) or not -500<=h<=9000 for h in heights):
        raise ValueError('Terrain has missing or invalid elevations')
    terrain=output/'rochester-terrain'
    terrain.mkdir(exist_ok=True)
    write_json(terrain/'terrain.json',{'width':129,'height':129,'heights_m':heights,
        'reference_height_m':heights[len(heights)//2],
        'vertical_datum':'USGS 3DEP source vertical datum not resolved by trial; not converted to ellipsoid'})
    write_json(terrain/'manifest.json',{'schema':1,'title':'Rochester staged 3DEP trial',
        'attribution':'USGS 3DEP · The National Map','bounds_deg':BOUNDS,
        'sha256':digest(terrain/'terrain.json'),'rights':'Public-domain USGS 3DEP',
        'rights_reference':RIGHTS['terrain'],'source_records':plan['terrain']})
    for root in (imagery,terrain):write_json(root/'source-plan.json',plan)
    LocalImageryPack.load(imagery)
    load_terrain(terrain)
    for kind,root,packager in (('imagery',imagery,package_imagery),('terrain',terrain,package_terrain)):
        descriptor=packager(root,output/f'rochester-{kind}.zip','rochester')
        descriptor.update(build_profile='static-source-trial-4096px-129grid',build_revision='static-source-trial-v1',
                          build_fingerprint=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest())
        write_json(output/f'rochester-{kind}.zip.json',descriptor)
    return {'imagery_bytes':(imagery/'imagery.jpg').stat().st_size,
            'terrain_range_m':[min(heights),max(heights)],'terrain_grid':[129,129]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--imagery-source',choices=('usgs','planetary-computer'),default='usgs')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    args.cache.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    report={'status':'started','bounds_deg':BOUNDS,'source_payload_cap_bytes':MAX_SOURCE_BYTES}
    try:
        plan=discover(args.output,args.imagery_source)
        write_json(args.output/'source-plan.json',plan)
        files={};receipts={};remaining=MAX_SOURCE_BYTES
        for kind in ('imagery','terrain'):
            files[kind]=[];receipts[kind]=[]
            for item in plan[kind]:
                path,receipt=(crop_cog(item['url'],args.cache,remaining)
                              if kind=='imagery' and args.imagery_source=='planetary-computer'
                              else download_source(item['url'],args.cache,remaining))
                remaining-=receipt['bytes']
                info=subprocess.run(['gdalinfo','-json',str(path)],check=True,capture_output=True,text=True,timeout=60)
                if len(info.stdout)>4*1024*1024:raise ValueError('Source raster metadata exceeds trial cap')
                receipt={**receipt,'raster_info':json.loads(info.stdout)}
                files[kind].append(path);receipts[kind].append(receipt)
        plan['download_receipts']=receipts
        report.update(process(plan,files,args.output),status='validated',cached_source_bytes=MAX_SOURCE_BYTES-remaining)
    except Exception as error:
        report.update(status='failed',error=str(error))
        raise
    finally:
        report['elapsed_seconds']=round(time.monotonic()-started,2)
        write_json(args.output/'trial-report.json',report)


if __name__=='__main__':main()
