# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Validate generated OpenRoadCode map artifacts."""
from __future__ import annotations
import gzip,hashlib,json,os,sqlite3,subprocess
from pathlib import Path
class ValidationError(RuntimeError):pass
def _run(cmd):return subprocess.run(cmd,text=True,capture_output=True,check=True)
def sha256(path):
 d=hashlib.sha256()
 with path.open("rb") as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b""):d.update(chunk)
 return d.hexdigest()
def validate_pbf(path):
 if not path.is_file() or path.stat().st_size==0:raise ValidationError(f"Missing/empty OSM PBF: {path}")
 _run(["osmium","fileinfo","-e",str(path)])
def _decode_vector_tile(blob):
 try:
  import mapbox_vector_tile
 except ImportError:
  return None
 if blob[:2]==b"\x1f\x8b":blob=gzip.decompress(blob)
 return mapbox_vector_tile.decode(blob)
def _vector_tile_rows(db,tile_count):
 full_scan=os.environ.get("OPENROAD_VECTOR_TILE_FULL_SCAN","0").lower() in {"1","true","yes","on"}
 limit=int(os.environ.get("OPENROAD_VECTOR_TILE_SCAN_LIMIT","0"))
 if full_scan:return db.execute("SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles ORDER BY zoom_level,tile_column,tile_row")
 if limit<=0:return ()
 zooms=[row[0] for row in db.execute("SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level")]
 per_zoom=max(1,limit//max(1,len(zooms)))
 rows=[]
 for zoom in zooms:
  rows.extend(db.execute("SELECT zoom_level,tile_column,tile_row,tile_data FROM tiles WHERE zoom_level=? ORDER BY tile_column,tile_row LIMIT ?",(zoom,per_zoom)))
 return rows[:limit]
def validate_vector_tiles(db,tile_count):
 rows=_vector_tile_rows(db,tile_count); checked=0
 for zoom,column,row,blob in rows:
  try:
   decoded=_decode_vector_tile(blob)
  except Exception as exc:
   raise ValidationError(f"Invalid vector tile z={zoom} x={column} y={row}: {exc}") from exc
  if decoded is None:return {"checked":0,"decoder":"unavailable"}
  checked+=1
 return {"checked":checked,"decoder":"mapbox-vector-tile"}
def validate_mbtiles(path):
 if not path.is_file() or path.stat().st_size==0:raise ValidationError(f"Missing/empty MBTiles: {path}")
 with sqlite3.connect(path) as db:
  integrity=db.execute("PRAGMA integrity_check").fetchone()[0]
  if integrity!="ok":raise ValidationError(f"MBTiles integrity check failed: {integrity}")
  tile_count=db.execute("SELECT COUNT(*) FROM tiles").fetchone()[0]; metadata=dict(db.execute("SELECT name, value FROM metadata"))
  vector_validation=validate_vector_tiles(db,tile_count)
 if tile_count<=0:raise ValidationError("MBTiles contains no tiles")
 layers={x.get("id") for x in json.loads(metadata.get("json","{}")).get("vector_layers",[]) if isinstance(x,dict)}; missing={"transportation","transportation_name"}-layers
 if missing:raise ValidationError("MBTiles missing required layer(s): "+", ".join(sorted(missing)))
 return {"tiles":tile_count,"layers":sorted(x for x in layers if x),"vector_tiles":vector_validation}
def validate_style(path,available_layers=None):
 data=json.loads(path.read_text(encoding="utf-8")); sources=data.get("sources") or {}
 if data.get("version")!=8:raise ValidationError("Style is not MapLibre/Mapbox Style Spec version 8")
 for source in ("openroad","route","vehicle"):
  if source not in sources:raise ValidationError(f"Style missing source: {source}")
 for source in ("vehicle","route"):
  if (sources[source].get("data") or {}).get("type")!="FeatureCollection":raise ValidationError(f"{source.title()} GeoJSON source is malformed")
 if available_layers is not None:
  referenced={layer.get("source-layer") for layer in data.get("layers",[]) if layer.get("source")=="openroad" and layer.get("source-layer")}
  missing=referenced-set(available_layers)
  if missing:raise ValidationError("Style references unavailable MBTiles layer(s): "+", ".join(sorted(missing)))
def validate_glyphs(path):
 files=list(path.rglob("*.pbf")) if path.exists() else []
 if len(files)<10 or not any(p.name=="0-255.pbf" for p in files):raise ValidationError(f"Invalid glyph set under {path}")
 return len(files)
def validate_valhalla(root,*,service_smoke=False):
 config=root/"valhalla.json"; tiles=root/"tiles"; extract=root/"tiles.tar"; admins=root/"admins.sqlite"; timezones=root/"timezones.sqlite"; json.loads(config.read_text(encoding="utf-8")); tile_files=[p for p in tiles.rglob("*") if p.is_file()]
 if not tile_files:raise ValidationError("Valhalla tile directory is empty")
 for db_path in (admins,timezones):
  if not db_path.is_file() or db_path.stat().st_size==0:raise ValidationError(f"Missing/empty Valhalla database: {db_path}")
  with sqlite3.connect(db_path) as db:
   if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":raise ValidationError(f"SQLite integrity failed: {db_path}")
 if not extract.is_file() or extract.stat().st_size==0:raise ValidationError("Valhalla tile extract is missing or empty")
 result={"tile_files":len(tile_files),"extract_bytes":extract.stat().st_size}
 if service_smoke:
  import time,urllib.request
  proc=subprocess.Popen(["valhalla_service",str(config),"1"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   for _ in range(30):
    try:
     with urllib.request.urlopen("http://127.0.0.1:8002/status",timeout=1) as response:
      if response.status==200:result["service_status"]="ok";break
    except Exception:time.sleep(.5)
   else:raise ValidationError("Valhalla service smoke test failed")
  finally:proc.terminate()
 return result
def validate_output(root,*,service_smoke=False):
 pbfs=sorted((root/"maps/source").glob("*.osm.pbf"))
 if not pbfs:raise ValidationError("No source PBFs found")
 for pbf in pbfs:validate_pbf(pbf)
 mbtiles=root/"maps/vector/openroadcode.mbtiles"; style=root/"maps/styles/openroadcode.json"; valhalla=root/"valhalla"; result={"source_pbfs":len(pbfs),"mbtiles":validate_mbtiles(mbtiles),"glyph_files":validate_glyphs(root/"maps/glyphs"),"valhalla":validate_valhalla(valhalla,service_smoke=service_smoke)}; validate_style(style,result["mbtiles"]["layers"]); result["checksums"]={"mbtiles":sha256(mbtiles),"style":sha256(style),"valhalla_extract":sha256(valhalla/"tiles.tar")}; return result
