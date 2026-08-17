# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import os
from types import SimpleNamespace

from flask import Flask, jsonify, redirect, render_template_string, url_for

app = Flask(__name__)

ctx = SimpleNamespace()
_radio_stacks_attached = False
status = "Ready"


HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#0b0d10">
  <title>OpenRoadCode</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b0d10;
      --panel: #151a20;
      --panel-hover: #1d252d;
      --border: #34424f;
      --accent: #5aa9e6;
      --text: #f5f7f8;
      --muted: #aebac4;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      min-height: 100dvh;
      background: var(--bg);
      color: var(--text);
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      -webkit-tap-highlight-color: transparent;
    }

    header {
      position: sticky;
      top: 0;
      z-index: 10;
      padding: calc(14px + env(safe-area-inset-top)) 18px 14px;
      background: rgba(15, 19, 23, 0.94);
      border-bottom: 1px solid #242d35;
      backdrop-filter: blur(12px);
    }

    .brand {
      max-width: 900px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .brand-title {
      font-size: clamp(1.25rem, 5vw, 1.7rem);
      font-weight: 800;
      letter-spacing: 0.02em;
    }

    .brand-subtitle {
      color: var(--muted);
      font-size: 0.82rem;
      margin-top: 2px;
    }

    .online-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #64d37f;
      box-shadow: 0 0 12px rgba(100, 211, 127, 0.65);
      flex: 0 0 auto;
    }

    main {
      width: min(100%, 900px);
      margin: 0 auto;
      padding: 18px 14px calc(24px + env(safe-area-inset-bottom));
    }

    .section-title {
      color: var(--muted);
      margin: 2px 4px 12px;
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .launcher-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    form { margin: 0; }

    button {
      width: 100%;
      min-height: 118px;
      padding: 16px 12px;
      border: 1px solid var(--border);
      border-top: 4px solid var(--accent);
      border-radius: 16px;
      background: linear-gradient(180deg, #1b2229 0%, var(--panel) 100%);
      color: var(--text);
      font: inherit;
      font-size: 1.05rem;
      font-weight: 750;
      cursor: pointer;
      touch-action: manipulation;
    }

    button:active {
      transform: scale(0.98);
      background: var(--panel-hover);
    }

    .status {
      margin-top: 16px;
      padding: 14px 16px;
      border: 1px solid #27313a;
      border-radius: 14px;
      background: #101419;
      color: var(--muted);
      font-size: 0.92rem;
    }

    @media (min-width: 700px) {
      .launcher-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
      button { min-height: 135px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div>
        <div class="brand-title">OpenRoadCode</div>
        <div class="brand-subtitle">Mobile Web UI</div>
      </div>
      <div class="online-dot" title="Web UI online"></div>
    </div>
  </header>

  <main>
    <div class="section-title">Radio & Data</div>
    <div class="launcher-grid">
      <form action="/action/fm" method="post"><button type="submit">FM Radio</button></form>
      <form action="/action/weather" method="post"><button type="submit">Weather Radio</button></form>
      <form action="/action/ham" method="post"><button type="submit">HAM Radio</button></form>
      <form action="/action/aircraft" method="post"><button type="submit">Aircraft</button></form>
      <form action="/action/adsb" method="post"><button type="submit">ADS-B</button></form>
      <form action="/action/weather_dash" method="post"><button type="submit">Weather Dash</button></form>
    </div>

    <div class="status">{{ status }}</div>
  </main>
</body>
</html>
"""


def _attach_radio_stacks() -> None:
    """Attach hardware-backed launchers only when an action actually needs them."""
    global _radio_stacks_attached

    if _radio_stacks_attached:
        return

    from apps.stack.radioStack import attach_radio_stacks

    attach_radio_stacks(ctx)
    _radio_stacks_attached = True


ACTIONS = {
    "fm": ("fm_radio_launcher", "FM Radio toggled"),
    "weather": ("weather_radio_launcher", "Weather Radio toggled"),
    "ham": ("ham_radio_launcher", "HAM Radio toggled"),
    "aircraft": ("airband_radio_launcher", "Airband toggled"),
    "adsb": ("adsb_launcher", "ADS-B toggled"),
    "weather_dash": ("weather_dash_launcher", "Weather dashboard toggled"),
}


@app.get("/")
def index():
    return render_template_string(HTML, status=status)


@app.get("/healthz")
def healthz():
    return jsonify(status="ok", app="OpenRoadCode Web UI")


@app.post("/action/<action_name>")
def run_action(action_name: str):
    global status

    action = ACTIONS.get(action_name)
    if action is None:
        status = f"Unknown action: {action_name}"
        return redirect(url_for("index"))

    launcher_name, success_status = action

    try:
        _attach_radio_stacks()
        getattr(ctx, launcher_name).toggle()
        status = success_status
    except Exception as exc:  # Keep the web UI usable even when Pi hardware is unavailable.
        app.logger.exception("OpenRoadCode action failed: %s", action_name)
        status = f"{action_name} unavailable: {exc}"

    return redirect(url_for("index"))


if __name__ == "__main__":
    host = os.environ.get("OPENROADCODE_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("OPENROADCODE_WEB_PORT", "5000"))
    debug = os.environ.get("OPENROADCODE_WEB_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
