"""Generate bounded Web Mercator delivery cells for Michigan detail."""
import argparse
import json
import math
import re
from pathlib import Path

from development.maps.state_map_catalog import _BOUNDARIES
from tools.map_builder.builder.building_parts import inside_or_boundary

ROOT_ZOOM=10
IMAGE_ZOOM=16
TERRAIN_SPACING_M=30
PROFILE='mi-detail-z16-terrain30-v1'
MAX_CELL_ARCHIVE=600*1024*1024


def xy(lon,lat,zoom=ROOT_ZOOM):
    count=2**zoom
    return (max(0,min(count-1,int((lon+180)/360*count))),
            max(0,min(count-1,int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*count))))


def bounds(x,y,zoom=ROOT_ZOOM):
    count=2**zoom
    latitude=lambda row:math.degrees(math.atan(math.sinh(math.pi*(1-2*row/count))))
    return (x/count*360-180,latitude(y+1),(x+1)/count*360-180,latitude(y))


def cell_id(x,y):return f'mi-z{ROOT_ZOOM}-{x}-{y}'


def parse_cell(key):
    match=re.fullmatch(r'mi-z10-([0-9]{1,4})-([0-9]{1,4})',key)
    if not match:raise ValueError('Invalid Michigan detail cell ID')
    x,y=map(int,match.groups())
    if x>=2**ROOT_ZOOM or y>=2**ROOT_ZOOM:raise ValueError('Detail cell outside root grid')
    return x,y


def crosses(a,b,c,d):
    def side(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    return (max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0]))
            and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1]))
            and side(a,b,c)*side(a,b,d)<=0 and side(c,d,a)*side(c,d,b)<=0)


def intersects(polygon,box):
    w,s,e,n=box
    outer=polygon[0]
    if max(p[0] for p in outer)<w or min(p[0] for p in outer)>e or max(p[1] for p in outer)<s or min(p[1] for p in outer)>n:
        return False
    corners=[(w,s),(e,s),(e,n),(w,n),(w,s)]
    if any(w<=x<=e and s<=y<=n for x,y in outer):return True
    if any(inside_or_boundary(point,outer) and not any(inside_or_boundary(point,h) for h in polygon[1:]) for point in corners[:-1]):return True
    return any(crosses(a,b,c,d) for a,b in zip(outer,outer[1:]) for c,d in zip(corners,corners[1:]))


def plan():
    document=json.loads(_BOUNDARIES.read_text())
    feature=next(f for f in document['features'] if f['properties']['STUSAB']=='MI')
    polygons=feature['geometry']['coordinates']
    if feature['geometry']['type']=='Polygon':polygons=[polygons]
    points=[p for polygon in polygons for p in polygon[0]]
    west,south,east,north=min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)
    left,top=xy(west,north);right,bottom=xy(east,south)
    cells=[]
    for y in range(top,bottom+1):
        for x in range(left,right+1):
            extent=bounds(x,y)
            if any(intersects(polygon,extent) for polygon in polygons):
                cells.append(dict(id=cell_id(x,y),x=x,y=y,bounds_deg=extent))
    if not cells or len(cells)>768:raise ValueError('Michigan detail plan exceeds reviewed cell count')
    batches=[dict(id=str(i//3),cells=cells[i:i+3]) for i in range(0,len(cells),3)]
    if len(batches)>256:raise ValueError('Detail matrix exceeds Actions batch limit')
    # Keep cell/batch IDs stable for resume, but make useful city previews first.
    priority=[cell_id(*xy(lon,lat)) for lon,lat in [(-83.05,42.33),(-85.67,42.96),
              (-84.55,42.73),(-85.62,44.76),(-87.4,46.54)]]
    def order(batch):
        keys={c['id'] for c in batch['cells']}
        return next((i for i,key in enumerate(priority) if key in keys),len(priority)),int(batch['id'])
    batches.sort(key=order)
    return dict(schema=1,kind='michigan-detail-plan',profile=PROFILE,root_zoom=ROOT_ZOOM,
                imagery_zoom=IMAGE_ZOOM,terrain_spacing_m=TERRAIN_SPACING_M,cells=cells,batches=batches)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--github-output',type=Path);args=parser.parse_args();document=plan()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(document,indent=2))
    if args.github_output:
        with args.github_output.open('a') as stream:stream.write('matrix='+json.dumps([b['id'] for b in document['batches']])+'\n')
    print(f"Planned {len(document['cells'])} Michigan cells in {len(document['batches'])} bounded batches")


if __name__=='__main__':main()
