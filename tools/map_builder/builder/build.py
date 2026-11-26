# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build OpenRoadCode offline map and routing data."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from urllib.request import Request, urlopen

from .geofabrik import Region
from .poi_index import build_search_index
from .style import install_style
from .validate import validate_output

OUTPUT_ROOT=Path(os.environ.get("OPENROAD_OUTPUT_ROOT","/srv/openroadcode")); CACHE_ROOT=Path(os.environ.get("OPENROAD_CACHE_ROOT","/cache")); SCRATCH_ROOT=Path(os.environ.get("OPENROAD_SCRATCH_ROOT","/scratch")); STYLE_TEMPLATE=Path(os.environ.get("OPENROAD_STYLE_TEMPLATE","/opt/openroadcode-map-builder/templates/openroadcode-style.json")); TILEMAKER_CONFIG=Path("/opt/tilemaker/resources/config-openmaptiles.json"); TILEMAKER_PROCESS=Path("/opt/tilemaker/resources/process-openmaptiles.lua"); GLYPH_SOURCE=Path("/opt/klokantech-gl-fonts/KlokanTech Noto Sans CJK Regular")
REFERENCE_MAP_SOURCE=Path(os.environ.get("OPENROAD_REFERENCE_MAP_SOURCE","/opt/openroadcode-source/resources/maps"))
REFERENCE_MAP_FILES=("us_state_boundaries.geojson","us_state_internal_boundaries.geojson","world_country_boundaries.geojson","world_land.geojson","world_lakes.geojson")
CENSUS_PRIMARY_ROADS_VINTAGE=2026
CENSUS_PRIMARY_ROADS_URL=f"https://www2.census.gov/geo/tiger/TIGER{CENSUS_PRIMARY_ROADS_VINTAGE}/PRIMARYROADS/tl_{CENSUS_PRIMARY_ROADS_VINTAGE}_us_primaryroads.zip"
NATIONAL_FREEWAYS_PROCESS=Path("/opt/openroadcode-map-builder/templates/process-census-primary-roads.lua")
class BuildError(RuntimeError): pass
def run(cmd:list[str],*,cwd:Path|None=None)->None:
 print("+"," ".join(str(x) for x in cmd),flush=True); subprocess.run(cmd,cwd=cwd,check=True)


def _format_bytes(value: float) -> str:
 for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
  if value < 1024.0 or unit == "TiB": return f"{value:.1f} {unit}"
  value /= 1024.0
 return f"{value:.1f} TiB"

def _print_download_progress(downloaded:int,total:int,started:float)->None:
 elapsed=max(time.monotonic()-started,0.001); speed=downloaded/elapsed
 if total>0:
  fraction=min(downloaded/total,1.0); width=30; filled=int(width*fraction); bar="#"*filled+"-"*(width-filled)
  print(f"\r  [{bar}] {fraction*100:6.2f}%  {_format_bytes(downloaded)} / {_format_bytes(total)}  {_format_bytes(speed)}/s",end="",flush=True)
 else: print(f"\r  Downloaded {_format_bytes(downloaded)}  {_format_bytes(speed)}/s",end="",flush=True)

def _download(url:str,destination:Path)->None:
 destination.parent.mkdir(parents=True,exist_ok=True)
 if destination.exists() and destination.stat().st_size>0: print(f"Using cached {destination.name}"); return
 tmp=destination.with_suffix(destination.suffix+".part")
 action="Resuming" if tmp.exists() and tmp.stat().st_size else "Downloading"
 print(f"{action} {url}",flush=True)
 run(["curl","--fail","--location","--retry","8","--retry-delay","5",
      "--retry-all-errors","--connect-timeout","30","--speed-limit","1024",
      "--speed-time","120","--continue-at","-","--user-agent",
      "OpenRoadCode-map-builder/1.0","--output",str(tmp),url])
 if not tmp.is_file() or tmp.stat().st_size<=0: raise BuildError(f"Download produced no data: {url}")
 tmp.replace(destination)
def _md5_file(path:Path)->str:
 digest=hashlib.md5()
 with path.open("rb") as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
 return digest.hexdigest().lower()
def _sha256_file(path:Path)->str:
 digest=hashlib.sha256()
 with path.open("rb") as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
 return digest.hexdigest().lower()
def _download_and_verify(region:Region,*,cache_root:Path|None=None)->Path:
 cached=(cache_root if cache_root is not None else CACHE_ROOT)/"pbf"/f"{region.safe_id}.osm.pbf"
 try:
  with urlopen(Request(region.pbf_url+".md5",headers={"User-Agent":"OpenRoadCode-map-builder/1.0"}),timeout=30) as response: expected=response.read().decode("utf-8",errors="replace").split()[0].lower()
 except Exception as exc:
  print(f"Warning: could not verify Geofabrik MD5 for {region.id}: {exc}")
  _download(region.pbf_url,cached)
 else:
  if cached.exists() and cached.stat().st_size>0:
   actual=_md5_file(cached)
   if actual==expected:
    print(f"Using cached {cached.name}")
   else:
    print(f"Cached {cached.name} is stale; refreshing from Geofabrik",flush=True)
    cached.unlink()
    _download(region.pbf_url,cached)
    actual=_md5_file(cached)
    if actual!=expected: raise BuildError(f"MD5 mismatch for freshly downloaded {region.id}")
  else:
   _download(region.pbf_url,cached)
   actual=_md5_file(cached)
   if actual!=expected: raise BuildError(f"MD5 mismatch for freshly downloaded {region.id}")
 run(["osmium","fileinfo","-e",str(cached)]); return cached
def _prepare_output_dirs(clean:bool)->None:
 if clean and OUTPUT_ROOT.exists():
  # A manifest certifies the complete artifact set. Invalidate it before
  # touching generated output so a failed rebuild can never leave an old
  # manifest beside a partially replaced dataset.
  (OUTPUT_ROOT/"build-manifest.json").unlink(missing_ok=True)
  for relative in ("maps/vector","maps/styles","maps/glyphs","maps/source","maps/poi","maps/search","maps/boundaries","maps/3d","valhalla"):
   target=OUTPUT_ROOT/relative
   if target.exists(): shutil.rmtree(target)
 for relative in ("maps/vector","maps/styles","maps/glyphs","maps/source","maps/search","maps/boundaries","maps/routes","valhalla/tiles"): (OUTPUT_ROOT/relative).mkdir(parents=True,exist_ok=True)
 SCRATCH_ROOT.mkdir(parents=True,exist_ok=True)
def _install_sources(regions,cached_pbfs):
 installed=[]
 for region,cached in zip(regions,cached_pbfs,strict=True):
  destination=OUTPUT_ROOT/"maps/source"/f"{region.safe_id}.osm.pbf"; shutil.copy2(cached,destination); installed.append(destination)
 return installed
BBOX_NUMBER=re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
def _parse_bbox(value:str)->str:
 numbers=[float(match) for match in BBOX_NUMBER.findall(value)]
 if len(numbers)!=4: raise BuildError(f"Could not parse merged map bounding box: {value!r}")
 west,south,east,north=numbers
 if not (-180<=west<=east<=180 and -90<=south<=north<=90): raise BuildError(f"Invalid merged map bounding box: {value!r}")
 return ",".join(format(number,".12g") for number in numbers)
def _pbf_bbox(pbf:Path)->str:
 result=subprocess.run(["osmium","fileinfo","-e","-g","data.bbox",str(pbf)],check=True,capture_output=True,text=True); return _parse_bbox(result.stdout.strip())
def _merge_for_build(pbfs):
 if len(pbfs)==1:return pbfs[0],None
 history=SCRATCH_ROOT/"selected-regions-history.osh.pbf"; merged=SCRATCH_ROOT/"selected-regions.osm.pbf"
 history.unlink(missing_ok=True); merged.unlink(missing_ok=True)
 # Adjacent Geofabrik extracts overlap at their boundaries and can contain
 # different versions of the same OSM object. Preserve those versions while
 # merging, then collapse the history to the newest object state before any
 # consumer (osmium export, tilemaker, Valhalla) sees the combined dataset.
 run(["osmium","merge","--with-history","--overwrite","-f","pbf,history=true","-o",str(history),*(str(p) for p in pbfs)])
 run(["osmium","time-filter","--overwrite","-o",str(merged),str(history)])
 run(["osmium","fileinfo","-e",str(merged)])
 return merged,_pbf_bbox(merged)
def _build_vector_tiles(tilemaker_input:Path,output:Path,store_name:str,bbox=None)->None:
 output.unlink(missing_ok=True); store=SCRATCH_ROOT/store_name
 if store.exists():shutil.rmtree(store)
 store.mkdir(parents=True); command=["tilemaker","--input",str(tilemaker_input),"--output",str(output),"--config",str(TILEMAKER_CONFIG),"--process",str(TILEMAKER_PROCESS),"--store",str(store)]
 if bbox: command.extend(["--bbox",bbox])
 run(command)
def _build_maplibre_data(tilemaker_input,bbox=None):
 _build_vector_tiles(tilemaker_input,OUTPUT_ROOT/"maps/vector/openroadcode.mbtiles","tilemaker-store",bbox)
 install_style(STYLE_TEMPLATE,OUTPUT_ROOT/"maps/styles/openroadcode.json"); glyph_dest=OUTPUT_ROOT/"maps/glyphs/KlokanTech Noto Sans CJK Regular"
 if glyph_dest.exists():shutil.rmtree(glyph_dest)
 shutil.copytree(GLYPH_SOURCE,glyph_dest)
 boundary_dest=OUTPUT_ROOT/"maps/boundaries"; boundary_dest.mkdir(parents=True,exist_ok=True)
 for name in REFERENCE_MAP_FILES:
  source=REFERENCE_MAP_SOURCE/name
  if not source.is_file(): raise BuildError(f"Missing reference map asset: {source}")
  shutil.copy2(source,boundary_dest/name)
def _national_freeway_archive()->Path:
 archive=CACHE_ROOT/"census"/f"tl_{CENSUS_PRIMARY_ROADS_VINTAGE}_us_primaryroads.zip"
 _download(CENSUS_PRIMARY_ROADS_URL,archive)
 return archive
def _national_freeway_source_record(archive:Path|None=None)->dict:
 record={"dataset":"U.S. Census Bureau TIGER/Line Primary Roads","vintage":CENSUS_PRIMARY_ROADS_VINTAGE,"url":CENSUS_PRIMARY_ROADS_URL,"path":"maps/vector/us-freeways.mbtiles"}
 if archive is not None and archive.is_file(): record["archive_sha256"]=_sha256_file(archive)
 return record
def _build_national_freeways(archive:Path|None=None)->dict:
 archive=archive or _national_freeway_archive(); source_name=f"tl_{CENSUS_PRIMARY_ROADS_VINTAGE}_us_primaryroads.shp"
 source=f"/vsizip/{archive}/{source_name}"; converted=SCRATCH_ROOT/"us-primary-roads"; shapefile=converted/source_name
 if converted.exists(): shutil.rmtree(converted)
 converted.mkdir(parents=True)
 run(["ogr2ogr","-f","ESRI Shapefile","-t_srs","EPSG:4326",str(shapefile),source])
 config=SCRATCH_ROOT/"census-primary-roads.json"
 config.write_text(json.dumps({
  "layers":{
   "transportation":{"minzoom":4,"maxzoom":14,"source":str(shapefile),"source_columns":["FULLNAME","RTTYP","MTFCC"],"simplify_below":12,"simplify_level":0.0001,"combine_lines_below":10},
   "transportation_name":{"minzoom":7,"maxzoom":14,"source":str(shapefile),"source_columns":["FULLNAME","RTTYP","MTFCC"],"simplify_below":12,"simplify_level":0.0001}
  },
  "settings":{"minzoom":4,"maxzoom":14,"basezoom":14,"include_ids":False,"compress":"gzip","name":"OpenRoadCode US primary roads","version":str(CENSUS_PRIMARY_ROADS_VINTAGE),"description":"Nationwide freeway overview from U.S. Census Bureau TIGER/Line Primary Roads","bounding_box":[-180,-90,180,90]}
 },indent=2)+"\n",encoding="utf-8")
 output=OUTPUT_ROOT/"maps/vector/us-freeways.mbtiles"; output.unlink(missing_ok=True); store=SCRATCH_ROOT/"tilemaker-freeways-store"
 if store.exists(): shutil.rmtree(store)
 store.mkdir(parents=True)
 run(["tilemaker","--output",str(output),"--config",str(config),"--process",str(NATIONAL_FREEWAYS_PROCESS),"--store",str(store)])
 return _national_freeway_source_record(archive)
def _build_valhalla(pbf:Path):
 root=OUTPUT_ROOT/"valhalla"; tiles=root/"tiles"
 if tiles.exists():shutil.rmtree(tiles)
 tiles.mkdir(parents=True); config=root/"valhalla.json"; admins=root/"admins.sqlite"; timezones=root/"timezones.sqlite"; extract=root/"tiles.tar"
 for path in (config,admins,timezones,extract):path.unlink(missing_ok=True)
 cmd=["valhalla_build_config","--mjolnir-tile-dir",str(tiles),"--mjolnir-tile-extract",str(extract),"--mjolnir-timezone",str(timezones),"--mjolnir-admin",str(admins)]
 with config.open("w",encoding="utf-8") as output:subprocess.run(cmd,check=True,stdout=output)
 with timezones.open("wb") as output:subprocess.run(["valhalla_build_timezones"],check=True,stdout=output)
 run(["valhalla_build_admins","-c",str(config),str(pbf)]); run(["valhalla_build_tiles","-c",str(config),str(pbf)]); run(["valhalla_build_extract","-c",str(config),"-v"])
def _write_manifest(regions,validation,search_counts,national_freeways:dict|None=None):
 manifest={"schema":2,"generated_unix":int(time.time()),"regions":[asdict(r) for r in regions],"validation":validation,"map_3d":validation.get("map_3d",{}),"search_index":{"counts":search_counts,"path":"maps/search/openroadcode-search.sqlite"},"tools":{}}
 manifest["national_freeways"]=national_freeways or _national_freeway_source_record()
 manifest["deployable_bytes"] = sum(p.stat().st_size for p in OUTPUT_ROOT.rglob("*") if p.is_file() and p.name != "build-manifest.json")
 for tool in ("tilemaker","valhalla_service","osmium","ogr2ogr"):
  result=subprocess.run([tool,"--version"],text=True,capture_output=True,check=False); manifest["tools"][tool]=(result.stdout or result.stderr).strip().splitlines()[0]
 (OUTPUT_ROOT/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
def build_regions(regions:list[Region],*,clean:bool=True,service_smoke:bool=True)->dict:
 if not regions:raise BuildError("No regions selected")
 freeway_source=_national_freeway_archive()
 _prepare_output_dirs(clean=clean); cached=[_download_and_verify(r) for r in regions]; installed=_install_sources(regions,cached); build_input,bbox=_merge_for_build(installed)
 search_counts=build_search_index(build_input,OUTPUT_ROOT/"maps/search/openroadcode-search.sqlite"); print(f"Built search index: {search_counts}",flush=True)
 _build_maplibre_data(build_input,bbox); freeway_record=_build_national_freeways(freeway_source); _build_valhalla(build_input); validation=validate_output(OUTPUT_ROOT,service_smoke=service_smoke); _write_manifest(regions,validation,search_counts,freeway_record); return validation
