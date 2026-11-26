"""Compile the lake-aware material in real headless Chromium, not a GL mock."""
import json
import math
import re
import shutil
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.launchers.cesium_sdk import sdk_directory

ROOT = Path(__file__).resolve().parents[3]
HTML = b'''<!doctype html><html><head><script>window.CESIUM_BASE_URL='/';</script>
<script src="/Cesium.js"></script><script src="/terrain_cues.js"></script>
<style>html,body,#map{width:100%;height:100%;margin:0}</style></head>
<body data-result="pending"><div id="map"></div><script>
try {
const viewer=new Cesium.Viewer('map',{baseLayer:false,geocoder:false,animation:false,timeline:false,
  skyBox:false,skyAtmosphere:false,homeButton:false,baseLayerPicker:false,navigationHelpButton:false,useDefaultRenderLoop:false});
viewer.scene.renderError.addEventListener((scene,error)=>{document.body.dataset.result='FAIL: '+error.message;});
const scheme=new Cesium.GeographicTilingScheme();
viewer.terrainProvider=new Cesium.CustomHeightmapTerrainProvider({width:33,height:33,tilingScheme:scheme,
 callback:(x,y,level)=>{const rectangle=scheme.tileXYToRectangle(x,y,level);const heights=new Float32Array(33*33);
 for(let row=0;row<33;row++)for(let col=0;col<33;col++)heights[row*33+col]=Cesium.Math.toDegrees(rectangle.north-(rectangle.north-rectangle.south)*row/32)*20;return heights;}});
viewer.camera.lookAt(Cesium.Cartesian3.fromDegrees(-87,44,880),new Cesium.HeadingPitchRange(0,-Math.PI/2,1000000));
viewer.scene.globe.baseColor=Cesium.Color.fromCssColorString('#174963');
viewer.scene.globe.showGroundAtmosphere=false;viewer.scene.fog.enabled=false;
viewer.scene.light=new Cesium.DirectionalLight({direction:viewer.camera.directionWC.clone()});
const cues=window.ORCTerrainCues(viewer,Cesium);
cues.setEnabled(true);cues.setScale(4);
let frames=0,water=null,finished=false;
viewer.scene.postRender.addEventListener(()=>{
 if(finished||++frames<=40||!viewer.scene.globe.tilesLoaded||document.body.dataset.result.startsWith('FAIL'))return;
 const context=viewer.scene.context||viewer.scene._context;
 const pixels=context.readPixels({x:Math.floor(viewer.canvas.width/2)-5,y:Math.floor(viewer.canvas.height/2)-5,width:11,height:11});
 let pixel=[0,0,0,0];for(let offset=0;offset<pixels.length;offset+=4)if(pixels[offset+1]>pixel[1])pixel=Array.from(pixels.slice(offset,offset+4));
 if(!water){water=pixel;frames=0;viewer.camera.lookAt(Cesium.Cartesian3.fromDegrees(-98,38,760),new Cesium.HeadingPitchRange(0,-Math.PI/2,1000000));return;}
 finished=true;
 document.body.dataset.result=pixel[1]>water[1]+8?'PASS':'FAIL: lake/land contour pixels '+JSON.stringify({water,land:pixel});
});
setInterval(()=>{try{viewer.render();}catch(error){document.body.dataset.result='FAIL: '+error.message;}},50);
} catch(error){document.body.dataset.result='FAIL: '+error.message;}
</script></body></html>'''


RELIEF_HTML = b'''<!doctype html><html><head><script>window.CESIUM_BASE_URL='/';</script>
<script src="/Cesium.js"></script><script src="/local_terrain.js"></script>
<style>html,body,#map{width:100%;height:100%;margin:0}</style></head>
<body data-result="pending"><div id="map"></div><script>
(async()=>{try {
const C=Cesium,viewer=new C.Viewer('map',{baseLayer:false,geocoder:false,animation:false,timeline:false,
 skyBox:false,skyAtmosphere:false,homeButton:false,baseLayerPicker:false,navigationHelpButton:false,useDefaultRenderLoop:false});
viewer.scene.renderError.addEventListener((scene,error)=>{document.body.dataset.result='FAIL: '+error.message;});
const terrain=window.ORCLocalTerrain({tiles:[],mesh_url:'/mesh/{z}/{x}/{y}',maximum_zoom:16},C,
 [C.Math.toRadians(-88.5),C.Math.toRadians(47.5)]);
await terrain.ready;terrain.setScale(viewer,4);terrain.setVisible(viewer,true);
viewer.scene.globe.showGroundAtmosphere=false;viewer.scene.fog.enabled=false;
viewer.camera.lookAt(C.Cartesian3.fromDegrees(-88.5,47.5,1600),new C.HeadingPitchRange(0,-Math.PI/4,16000));
let frames=0;
viewer.scene.postRender.addEventListener(()=>{
 if(++frames<40||!viewer.scene.globe.tilesLoaded||document.body.dataset.result.startsWith('FAIL'))return;
 const peak=viewer.scene.globe.getHeight(C.Cartographic.fromDegrees(-88.5,47.5));
 const lower=viewer.scene.globe.getHeight(C.Cartographic.fromDegrees(-88.58,47.5));
 if(peak===undefined||lower===undefined)return;
 document.body.dataset.result=peak>1450&&peak-lower>600?'PASS':'FAIL: rendered relief '+JSON.stringify({peak,lower});
});
setInterval(()=>{try{viewer.render();}catch(error){document.body.dataset.result='FAIL: '+error.message;}},50);
}catch(error){document.body.dataset.result='FAIL: '+error.message;}})();
</script></body></html>'''


def relief_sampler():
    from apps.launchers.terrain_mesh_sampler import TerrainMeshSampler, TerrainSource
    from ui.navigation.local_imagery_state import LocalImageryState
    from ui.navigation.local_terrain_state import LocalTerrainState
    bounds=tuple(map(math.radians,(-89,47,-88,48)))
    heights=tuple(100+300*math.exp(-((row-64)**2+(col-64)**2)/100)
                  for row in range(129) for col in range(129))
    state=LocalTerrainState(LocalImageryState('UP hill','test',*bounds),129,129,heights,0,'source')
    source=TerrainSource('hill',bounds,129,129,7,lambda:state)
    class Index:
        def point_sources(self,x,y):return [source] if source.supports(x,y) else []
    return TerrainMeshSampler(SimpleNamespace(state=SimpleNamespace(tiles=()),payloads=(),index=Index()))


@pytest.mark.parametrize('scenario',['water-material','rendered-relief'])
def test_local_terrain_in_chromium(tmp_path, scenario):
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    sdk = sdk_directory()
    if not chrome or not (sdk/'Cesium.js').is_file():
        pytest.skip('Requires installed Chromium and pinned Cesium SDK')
    seen = []
    sampler=relief_sampler() if scenario=='rendered-relief' else None
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/test.html':
                body, mime = (RELIEF_HTML if sampler else HTML), 'text/html'
            elif self.path.startswith('/mesh/') and sampler:
                body,mime=json.dumps(sampler.mesh(*map(int,self.path.split('/')[2:]))).encode(),'application/json'
                seen.append('mesh')
            elif self.path == '/local_terrain.js':
                body,mime=(ROOT/'frontends/web/cesium/local_terrain.js').read_bytes(),'text/javascript'
            elif self.path == '/terrain_cues.js':
                body, mime = (ROOT/'frontends/web/cesium/terrain_cues.js').read_bytes(), 'text/javascript'
            elif self.path == '/data/world-reference.png':
                body, mime = (ROOT/'resources/maps/world_reference.png').read_bytes(), 'image/png'
                seen.append('water-mask')
            else:
                return super().do_GET()
            self.send_response(200);self.send_header('Content-Type',mime)
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(sdk)))
    worker = threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        result = subprocess.run([chrome,'--headless','--no-sandbox','--disable-dev-shm-usage',
            '--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader',
            '--user-data-dir='+str(tmp_path/'profile'),'--virtual-time-budget=20000','--dump-dom',
            f'http://127.0.0.1:{server.server_port}/test.html'],capture_output=True,text=True,timeout=60)
        status=re.search(r'data-result="([^"]+)"',result.stdout)
        assert status and status[1]=='PASS', (status[1] if status else 'No browser result')+result.stderr[-1000:]
        assert ('mesh' if sampler else 'water-mask') in seen, 'Actual terrain transport/texture was never requested'
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)
