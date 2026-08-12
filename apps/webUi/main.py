# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from flask import Flask, redirect, render_template_string, url_for
from types import SimpleNamespace

from apps.stack.radioStack import attach_radio_stacks

app = Flask(__name__)

ctx = SimpleNamespace()
attach_radio_stacks(ctx)

HTML = """
<!doctype html>
<html>
<head>
  <title>CarSDR Web</title>
  <style>
    body {
      margin: 0;
      background: #111418;
      color: #fff;
      font-family: Arial, sans-serif;
    }s
    header {
      background: #dfe7eb;
      color: #1d2429;
      padding: 1rem;
      font-size: 1.4rem;
      font-weight: bold;
    }
    main {
      padding: 1rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 1rem;
    }
    button {
      width: 100%;
      min-height: 100px;
      background: #20252b;
      color: white;
      border: 2px solid #384653;
      border-top: 5px solid #5aa9e6;
      border-radius: 14px;
      font-size: 1.2rem;
      font-weight: bold;
    }
    .status {
      padding: 1rem;
      color: #b8c7d3;
      background: #0b0d10;
    }
  </style>
</head>
<body>
  <header>Mark's CarSDR Web</header>

  <main>
    <form action="/fm" method="post"><button>FM Radio</button></form>
    <form action="/weather" method="post"><button>Weather Radio</button></form>
    <form action="/ham" method="post"><button>HAM Radio</button></form>
    <form action="/aircraft" method="post"><button>Aircraft</button></form>
    <form action="/adsb" method="post"><button>ADS-B</button></form>
    <form action="/weather_dash" method="post"><button>Weather Dash</button></form>
  </main>

  <div class="status">{{ status }}</div>
</body>
</html>
"""

status = "Ready"


@app.get("/")
def index():
    return render_template_string(HTML, status=status)


@app.post("/fm")
def fm():
    global status
    ctx.fm_radio_launcher.toggle()
    status = "FM Radio toggled"
    return redirect(url_for("index"))


@app.post("/weather")
def weather():
    global status
    ctx.weather_radio_launcher.toggle()
    status = "Weather Radio toggled"
    return redirect(url_for("index"))


@app.post("/ham")
def ham():
    global status
    ctx.ham_radio_launcher.toggle()
    status = "HAM Radio toggled"
    return redirect(url_for("index"))


@app.post("/aircraft")
def aircraft():
    global status
    ctx.airband_radio_launcher.toggle()
    status = "Airband toggled"
    return redirect(url_for("index"))


@app.post("/adsb")
def adsb():
    global status
    ctx.adsb_launcher.toggle()
    status = "ADS-B toggled"
    return redirect(url_for("index"))


@app.post("/weather_dash")
def weather_dash():
    global status
    ctx.weather_dash_launcher.toggle()
    status = "Weather dashboard toggled"
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
