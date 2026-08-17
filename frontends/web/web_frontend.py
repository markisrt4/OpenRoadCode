# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Flask renderer for toolkit-independent OpenRoadCode menu models."""

from __future__ import annotations

from collections.abc import Mapping

from flask import Flask, abort, jsonify, redirect, render_template_string, url_for

from ui.menu import MenuPage


PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#0b0d10">
  <title>{{ page.title }} | OpenRoadCode</title>
  <style>
    :root { color-scheme: dark; --bg:#0b0d10; --panel:#151a20; --hover:#1d252d; --border:#34424f; --accent:#5aa9e6; --text:#f5f7f8; --muted:#aebac4; }
    * { box-sizing: border-box; }
    body { margin:0; min-height:100vh; min-height:100dvh; background:var(--bg); color:var(--text); font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; -webkit-tap-highlight-color:transparent; }
    header { position:sticky; top:0; z-index:10; padding:calc(14px + env(safe-area-inset-top)) 16px 14px; background:rgba(15,19,23,.94); border-bottom:1px solid #242d35; backdrop-filter:blur(12px); }
    .bar { width:min(100%,900px); margin:0 auto; display:flex; align-items:center; gap:12px; }
    .back { width:44px; height:44px; border:1px solid var(--border); border-radius:12px; display:grid; place-items:center; color:var(--text); text-decoration:none; font-size:1.4rem; flex:0 0 auto; }
    .heading { flex:1; min-width:0; }
    .title { font-size:clamp(1.25rem,5vw,1.7rem); font-weight:800; letter-spacing:.02em; }
    .subtitle { color:var(--muted); font-size:.8rem; margin-top:2px; }
    .online { width:10px; height:10px; border-radius:50%; background:#64d37f; box-shadow:0 0 12px rgba(100,211,127,.65); }
    main { width:min(100%,900px); margin:0 auto; padding:18px 14px calc(24px + env(safe-area-inset-bottom)); }
    .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
    .tile { min-height:132px; padding:16px; border:1px solid var(--border); border-top:4px solid var(--accent); border-radius:16px; background:linear-gradient(180deg,#1b2229 0%,var(--panel) 100%); color:var(--text); text-decoration:none; display:flex; flex-direction:column; justify-content:center; touch-action:manipulation; }
    .tile:active { transform:scale(.98); background:var(--hover); }
    .tile-title { font-size:1.05rem; font-weight:800; letter-spacing:.03em; }
    .tile-subtitle { margin-top:7px; color:#d9e0e5; font-size:.88rem; }
    .tile-detail { margin-top:5px; color:var(--muted); font-size:.76rem; line-height:1.25; }
    .placeholder { margin-top:18px; padding:16px; border:1px solid #27313a; border-radius:14px; color:var(--muted); background:#101419; }
    @media (min-width:700px) { .grid { grid-template-columns:repeat(3,minmax(0,1fr)); } .tile { min-height:145px; } }
  </style>
</head>
<body>
<header>
  <div class="bar">
    {% if page_key != root_page %}<a class="back" href="{{ url_for('menu_page', page_key=root_page) }}" aria-label="Home">‹</a>{% endif %}
    <div class="heading"><div class="title">{{ page.title }}</div><div class="subtitle">OpenRoadCode Web</div></div>
    <div class="online" title="Web frontend online"></div>
  </div>
</header>
<main>
  <div class="grid">
    {% for tile in page.tiles %}
      <a class="tile" href="{{ url_for('select_tile', page_key=page_key, tile_key=tile.key) }}">
        <div class="tile-title">{{ tile.title }}</div>
        <div class="tile-subtitle">{{ tile.subtitle }}</div>
        <div class="tile-detail">{{ tile.detail }}</div>
      </a>
    {% endfor %}
  </div>
  {% if message %}<div class="placeholder">{{ message }}</div>{% endif %}
</main>
</body>
</html>
"""


def create_web_frontend(
    pages: Mapping[str, MenuPage],
    *,
    root_page: str = "main",
) -> Flask:
    """Create a browser frontend without importing application or hardware code."""
    if root_page not in pages:
        raise ValueError(f"Unknown root page: {root_page}")

    app = Flask(__name__)

    @app.get("/")
    def index():
        return redirect(url_for("menu_page", page_key=root_page))

    @app.get("/menu/<page_key>")
    def menu_page(page_key: str):
        page = pages.get(page_key)
        if page is None:
            abort(404)
        return render_template_string(
            PAGE_TEMPLATE,
            page=page,
            page_key=page_key,
            root_page=root_page,
            message=None,
        )

    @app.get("/menu/<page_key>/<tile_key>")
    def select_tile(page_key: str, tile_key: str):
        page = pages.get(page_key)
        if page is None:
            abort(404)
        tile = next((item for item in page.tiles if item.key == tile_key), None)
        if tile is None:
            abort(404)

        if tile.key in pages:
            return redirect(url_for("menu_page", page_key=tile.key))

        return render_template_string(
            PAGE_TEMPLATE,
            page=page,
            page_key=page_key,
            root_page=root_page,
            message=f"{tile.title} web screen is not implemented yet.",
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok", frontend="web")

    return app
