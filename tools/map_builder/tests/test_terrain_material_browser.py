"""Compile the lake-aware material in real headless Chromium, not a GL mock."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import re
import subprocess
import threading

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
viewer.camera.lookAt(Cesium.Cartesian3.fromDegrees(-83,44),new Cesium.HeadingPitchRange(0,-Math.PI/2,1000000));
window.ORCTerrainCues(viewer,Cesium).setEnabled(true);
let frames=0;
viewer.scene.postRender.addEventListener(()=>{
 if(++frames>30&&viewer.scene.globe.tilesLoaded&&!document.body.dataset.result.startsWith('FAIL'))document.body.dataset.result='PASS';
});
setInterval(()=>{try{viewer.render();}catch(error){document.body.dataset.result='FAIL: '+error.message;}},50);
} catch(error){document.body.dataset.result='FAIL: '+error.message;}
</script></body></html>'''


def test_lake_contour_material_compiles_in_chromium(tmp_path):
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    sdk = sdk_directory()
    if not chrome or not (sdk/'Cesium.js').is_file():
        pytest.skip('Requires installed Chromium and pinned Cesium SDK')
    seen = []
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/test.html':
                body, mime = HTML, 'text/html'
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
            '--user-data-dir='+str(tmp_path/'profile'),'--virtual-time-budget=12000','--dump-dom',
            f'http://127.0.0.1:{server.server_port}/test.html'],capture_output=True,text=True,timeout=60)
        status=re.search(r'data-result="([^"]+)"',result.stdout)
        assert status and status[1]=='PASS', (status[1] if status else 'No browser result')+result.stderr[-1000:]
        assert seen, 'Actual material texture was never requested'
    finally:
        server.shutdown();server.server_close();worker.join(timeout=5)
