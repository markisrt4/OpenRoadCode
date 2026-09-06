# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Build OpenRoadCode offline map and routing data."""
from __future__ import annotations
from dataclasses import asdict
import hashlib, json, os, re, shutil, subprocess, time
from pathlib import Path
from urllib.request import Request, urlopen
from .geofabrik import Region
from .poi_index import build_search_index
from .style import install_style
from .validate import validate_output
OUTPUT_ROOT=Path(os.environ.get("OPENROAD_OUTPUT_ROOT","/srv/openroadcode")); CACHE_ROOT=Path(os.environ.get("OPENROAD_CACHE_ROOT","/cache")); SCRATCH_ROOT=Path(os.environ.get("OPENROAD_SCRATCH_ROOT","/scratch")); STYLE_TEMPLATE=Path(os.environ.get("OPENROAD_STYLE_TEMPLATE","/opt/openroadcode-map-builder/templates/openroadcode-style.json")); TILEMAKER_CONFIG=Path("/opt/tilemaker/resources/config-openmaptiles.json"); TILEMAKER_PROCESS=Path("/opt/tilemaker/resources/process-openmaptiles.lua"); GLYPH_SOURCE=Path("/opt/klokantech-gl-fonts/KlokanTech Noto Sans CJK Regular")
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
 tmp=destination.with_suffix(destination.suffix+".part"); request=Request(url,headers={"User-Agent":"OpenRoadCode-map-builder/1.0"}); print(f"Downloading {url}",flush=True)
 downloaded=0; started=time.monotonic()
 with urlopen(request,timeout=120) as response,tmp.open("wb") as output:
  content_length=response.headers.get("Content-Length"); total=int(content_length) if content_length and content_length.isdigit() else 0
  while True:
   chunk=response.read(1024*1024)
   if not chunk: break
   output.write(chunk); downloaded+=len(chunk); _print_download_progress(downloaded,total,started)
 print(flush=True); tmp.replace(destination)
def _download_and_verify(region:Region)->Path:
 cached=CACHE_ROOT/"pbf"/f"{region.safe_id}.osm.pbf"; _download(region.pbf_url,cached)
 try:
  with urlopen(Request(region.pbf_url+".md5",headers={"User-Agent":"OpenRoadCode-map-builder/1.0"}),timeout=30) as response: expected=response.read().decode("utf-8",errors="replace").split()[0].lower()
  digest=hashlib.md5()
  with cached.open("rb") as stream:
   for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
  if digest.hexdigest().lower()!=expected: raise BuildError(f"MD5 mismatch for {region.id}")
 except BuildError: raise
 except Exception as exc: print(f"Warning: could not verify Geofabrik MD5 for {region.id}: {exc}")
 run(["osmium","fileinfo","-e",str(cached)]); return cached
def _prepare_output_dirs(clean:bool)->None:
 if clean and OUTPUT_ROOT.exists():
  for relative in ("maps/vector","maps/styles","maps/glyphs","maps/source","maps/poi","maps/search","valhalla"):
   target=OUTPUT_ROOT/relative
   if target.exists(): shutil.rmtree(target)
 for relative in ("maps/vector","maps/styles","maps/glyphs","maps/source","maps/search","maps/routes","valhalla/tiles"): (OUTPUT_ROOT/relative).mkdir(parents=True,exist_ok=True)
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
 merged=SCRATCH_ROOT/"selected-regions.osm.pbf"; merged.unlink(missing_ok=True); run(["osmium","merge","--overwrite","-o",str(merged),*(str(p) for p in pbfs)]); return merged,_pbf_bbox(merged)
def _build_maplibre_data(tilemaker_input,bbox=None):
 output=OUTPUT_ROOT/"maps/vector/openroadcode.mbtiles"; output.unlink(missing_ok=True); store=SCRATCH_ROOT/"tilemaker-store"
 if store.exists():shutil.rmtree(store)
 store.mkdir(parents=True); command=["tilemaker","--input",str(tilemaker_input),"--output",str(output),"--config",str(TILEMAKER_CONFIG),"--process",str(TILEMAKER_PROCESS),"--store",str(store)]
 if bbox: command.extend(["--bbox",bbox])
 run(command); install_style(STYLE_TEMPLATE,OUTPUT_ROOT/"maps/styles/openroadcode.json"); glyph_dest=OUTPUT_ROOT/"maps/glyphs/KlokanTech Noto Sans CJK Regular"
 if glyph_dest.exists():shutil.rmtree(glyph_dest)
 shutil.copytree(GLYPH_SOURCE,glyph_dest)
def _build_valhalla(pbf:Path):
 root=OUTPUT_ROOT/"valhalla"; tiles=root/"tiles"
 if tiles.exists():shutil.rmtree(tiles)
 tiles.mkdir(parents=True); config=root/"valhalla.json"; admins=root/"admins.sqlite"; timezones=root/"timezones.sqlite"; extract=root/"tiles.tar"
 for path in (config,admins,timezones,extract):path.unlink(missing_ok=True)
 cmd=["valhalla_build_config","--mjolnir-tile-dir",str(tiles),"--mjolnir-tile-extract",str(extract),"--mjolnir-timezone",str(timezones),"--mjolnir-admin",str(admins)]
 with config.open("w",encoding="utf-8") as output:subprocess.run(cmd,check=True,stdout=output)
 with timezones.open("wb") as output:subprocess.run(["valhalla_build_timezones"],check=True,stdout=output)
 run(["valhalla_build_admins","-c",str(config),str(pbf)]); run(["valhalla_build_tiles","-c",str(config),str(pbf)]); run(["valhalla_build_extract","-c",str(config),"-v"])
def _write_manifest(regions,validation,search_counts):
 manifest={"schema":2,"generated_unix":int(time.time()),"regions":[asdict(r) for r in regions],"validation":validation,"search_index":{"counts":search_counts,"path":"maps/search/openroadcode-search.sqlite"},"tools":{}}
 for tool in ("tilemaker","valhalla_service","osmium"):
  result=subprocess.run([tool,"--version"],text=True,capture_output=True,check=False); manifest["tools"][tool]=(result.stdout or result.stderr).strip().splitlines()[0]
 (OUTPUT_ROOT/"build-manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
def build_regions(regions:list[Region],*,clean:bool=True,service_smoke:bool=True)->dict:
 if not regions:raise BuildError("No regions selected")
 _prepare_output_dirs(clean=clean); cached=[_download_and_verify(r) for r in regions]; installed=_install_sources(regions,cached); build_input,bbox=_merge_for_build(installed)
 search_counts=build_search_index(build_input,OUTPUT_ROOT/"maps/search/openroadcode-search.sqlite"); print(f"Built search index: {search_counts}",flush=True)
 _build_maplibre_data(build_input,bbox); _build_valhalla(build_input); validation=validate_output(OUTPUT_ROOT,service_smoke=service_smoke); _write_manifest(regions,validation,search_counts); return validation
