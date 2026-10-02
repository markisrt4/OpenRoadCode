# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Compact WebGL visualizer surface for embedded application hosts."""

VISUALIZER_HTML = '''<!doctype html>
<html data-color-scheme="dark"><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Music Visualizer</title>
<link rel="stylesheet" href="/web-assets/audio-analysis/music_visualizer.css">
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#05090d;color:#edf2f5;font:14px sans-serif}
button,select,input{font:inherit}button,select{padding:8px;background:#182530;color:inherit;border:1px solid #344654;border-radius:6px}
.controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:8px}
.card{background:#0b1117;padding:10px;margin:6px;border-radius:8px}p{margin:4px 8px;font-size:12px;color:#aebac4}
#mv-webgl-stage{margin:6px;padding:10px!important}#mv-webgl-canvas{height:calc(100vh - 220px)!important;min-height:200px}
#mv-webgl-stage:fullscreen #mv-webgl-canvas{height:calc(100vh - 100px)!important}
#music-visualizer-anchor{display:none}.calibration{display:flex;gap:6px;align-items:center}
html[data-color-scheme="light"]{color-scheme:light}
html[data-color-scheme="light"] body{background:#eef2f6;color:#152230}
html[data-color-scheme="light"] .card{background:#fff}
html[data-color-scheme="light"] button,html[data-color-scheme="light"] select{background:#e1e8ee}
html[data-color-scheme="light"] p{color:#435365}
</style></head><body>
<div class="controls"><button id="music-visualizer-toggle">START AUDIO</button>
<label>Sensitivity <input id="music-visualizer-sensitivity" type="range" min="1" max="20" value="10"></label>
<strong id="music-visualizer-sensitivity-value">10×</strong>
<div class="calibration"><button id="music-zeroize-start" disabled>CALIBRATE</button><button id="music-zeroize-finish" disabled>FINISH</button><button id="music-zeroize-clear" disabled>CLEAR</button></div></div>
<p id="music-visualizer-status">Choose an audio source and press START AUDIO.</p>
<p id="music-zeroize-status">No ambient-noise calibration.</p>
<div id="music-visualizer-anchor"></div>
<div hidden><div id="music-bass"></div><div id="music-mid"></div><div id="music-treble"></div></div>
<script src="/web-assets/audio-analysis/inline_select.js"></script>
<script src="/web-assets/audio-analysis/browser_pcm_capture.js"></script>
<script src="/web-assets/audio-analysis/webgl_music_visualizer.js"></script>
<script src="/web-assets/audio-analysis/music_visualizer.js"></script>
</body></html>'''
