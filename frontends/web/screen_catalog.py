# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Browser-native leaf screens used by the standalone web frontend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WebScreen:
    title: str
    subtitle: str
    body_html: str


def create_web_screens() -> dict[str, WebScreen]:
    """Create frontend-only screens safe to render on Termux or desktop Linux."""
    return {
        "vehicle_gauges": WebScreen(
            "Vehicle Gauges", "Mock telemetry mode",
            '''<div class="gauges">
              <div class="gauge"><span id="rpm">2450</span><small>RPM</small></div>
              <div class="gauge"><span id="speed">42</span><small>MPH</small></div>
              <div class="gauge"><span id="boost">4.2</span><small>BOOST PSI</small></div>
              <div class="gauge"><span id="throttle">31</span><small>THROTTLE %</small></div>
            </div>
            <div class="card"><b>Termux demo source</b><p>These values are generated in the browser. The screen is ready for a telemetry provider to be injected later.</p></div>
            <script>
            setInterval(() => {
              const t=Date.now()/1000;
              document.getElementById('rpm').textContent=Math.round(2200+700*Math.sin(t));
              document.getElementById('speed').textContent=Math.round(43+5*Math.sin(t/2));
              document.getElementById('boost').textContent=(4+3*Math.max(0,Math.sin(t))).toFixed(1);
              document.getElementById('throttle').textContent=Math.round(30+15*Math.sin(t/1.7));
            },250);
            </script>''',
        ),
        "weather_overview": WebScreen(
            "Weather", "Frontend provider shell",
            '''<div class="hero-value">72°<small>F</small></div>
            <div class="card"><b>Current Conditions</b><p>Partly cloudy</p></div>
            <div class="stat-grid"><div class="stat"><b>8 mph</b><small>WIND</small></div><div class="stat"><b>29.96</b><small>PRESSURE</small></div><div class="stat"><b>48%</b><small>HUMIDITY</small></div></div>
            <div class="notice">Demo data for mobile UI development. Weather data will come through an injected provider rather than being fetched by the view.</div>''',
        ),
        "weather_forecast": WebScreen("Forecast", "Demo forecast", '''<div class="forecast"><div><b>MON</b><span>72°</span><small>Partly cloudy</small></div><div><b>TUE</b><span>76°</span><small>Sunny</small></div><div><b>WED</b><span>69°</span><small>Rain</small></div><div><b>THU</b><span>73°</span><small>Cloudy</small></div></div>'''),
        "weather_alerts": WebScreen("Weather Alerts", "Warnings and watches", '''<div class="card"><b>No demo alerts</b><p>The provider contract will populate active warnings here.</p></div>'''),
        "fm_radio": WebScreen("FM Radio", "Frontend controls", '''<div class="hero-value" id="freq">101.1<small>MHz</small></div><div class="controls"><button onclick="tune(-.2)">−</button><button class="primary">PLAY</button><button onclick="tune(.2)">+</button></div><script>let f=101.1;function tune(d){f=Math.max(87.5,Math.min(108,f+d));document.getElementById('freq').firstChild.nodeValue=f.toFixed(1);}</script>'''),
        "scanner_radio": WebScreen("Scanner", "Monitoring controls", '''<div class="card"><b>Scanner idle</b><p>Hardware/backend connection is not attached in standalone mode.</p></div><div class="controls"><button class="primary">START SCAN</button><button>HOLD</button></div>'''),
        "weather_radio": WebScreen("NOAA Weather Radio", "Weather band", '''<div class="hero-value">162.550<small>MHz</small></div><div class="controls"><button>CH −</button><button class="primary">PLAY</button><button>CH +</button></div>'''),
        "adsb": WebScreen("ADS-B", "Nearby aircraft", '''<div class="card"><b>No ADS-B source attached</b><p>The web view is ready for aircraft data from the OpenRoadCode backend.</p></div>'''),
        "airband": WebScreen("Airband", "AM aviation radio", '''<div class="hero-value">118.000<small>MHz AM</small></div><div class="controls"><button>−</button><button class="primary">MONITOR</button><button>+</button></div>'''),
        "offroad_dashboard": WebScreen(
            "Off-Road", "Phone GPS + orientation",
            '''<div class="stat-grid">
              <div class="stat"><b id="pitch" class="sensor-value">--</b><small>PITCH</small></div>
              <div class="stat"><b id="roll" class="sensor-value">--</b><small>ROLL</small></div>
              <div class="stat"><b id="heading" class="sensor-value">--</b><small>HEADING</small></div>
              <div class="stat"><b id="speed" class="sensor-value">--</b><small>GPS MPH</small></div>
            </div>
            <div class="card">
              <b>Phone sensors</b>
              <p id="sensor-status" class="sensor-status">Tap START SENSORS to request browser access.</p>
              <div id="location" class="sensor-status">GPS: --</div>
              <button id="start-sensors" class="primary wide">START SENSORS</button>
            </div>
            <script src="/web-assets/sensors/device_orientation.js"></script>
            <script src="/web-assets/sensors/geolocation.js"></script>
            <script>
            (() => {
              const status=document.getElementById('sensor-status');
              const orientation=new OpenRoadCodeWeb.DeviceOrientationSensorAdapter();
              const geolocation=new OpenRoadCodeWeb.GeolocationSensorAdapter();
              const value=(id,v,digits=1,suffix='°') => {
                document.getElementById(id).textContent = Number.isFinite(v) ? `${v.toFixed(digits)}${suffix}` : '--';
              };
              document.getElementById('start-sensors').addEventListener('click', async () => {
                const messages=[];
                try {
                  const granted=await orientation.requestPermission();
                  if (granted) {
                    orientation.start((sample) => {
                      value('pitch',sample.pitchDeg);
                      value('roll',sample.rollDeg);
                      value('heading',sample.headingDeg,0);
                    },(error)=>{status.textContent=`Orientation: ${error.message}`;});
                    messages.push('orientation active');
                  } else messages.push('orientation permission denied');
                } catch(error) { messages.push(`orientation unavailable: ${error.message}`); }

                geolocation.start((sample) => {
                  const mph=Number.isFinite(sample.speedMps) ? sample.speedMps*2.236936 : null;
                  value('speed',mph,1,' mph');
                  document.getElementById('location').textContent =
                    `GPS: ${sample.latitude.toFixed(6)}, ${sample.longitude.toFixed(6)} ±${Math.round(sample.accuracyM)} m`;
                  if (!Number.isFinite(document.getElementById('heading').textContent.replace('°','')) && Number.isFinite(sample.headingDeg)) {
                    value('heading',sample.headingDeg,0);
                  }
                },(error)=>{status.textContent=`GPS: ${error.message}`;});
                if (geolocation.supported) messages.push('GPS requested');
                status.textContent=messages.join(' · ') || 'No browser sensors available.';
              });
            })();
            </script>''',
        ),
        "cabin_lighting": WebScreen("Cabin Lighting", "Frontend controls", '''<div class="card"><label>Brightness</label><input type="range" min="0" max="100" value="65"><label>Color</label><input type="color" value="#ff3030"></div>'''),
        "accent_lighting": WebScreen("Accent Lighting", "Frontend controls", '''<div class="card"><label>Brightness</label><input type="range" min="0" max="100" value="50"><label>Color</label><input type="color" value="#307cff"></div>'''),
        "spotify": WebScreen("Spotify", "Playback shell", '''<div class="album">♫</div><div class="card center"><b>Nothing playing</b><p>Spotify service not attached in standalone mode.</p></div><div class="controls"><button>◀</button><button class="primary">▶</button><button>▶▶</button></div>'''),
        "netflix": WebScreen("Netflix", "Browser integration", '''<div class="card"><b>Netflix launcher</b><p>External browser/application launching will be supplied by the host application, not the reusable frontend.</p></div>'''),
        "youtube": WebScreen("YouTube", "Video and search", '''<div class="card"><input class="search" placeholder="Search YouTube"><button class="primary wide">SEARCH</button></div>'''),
    }
