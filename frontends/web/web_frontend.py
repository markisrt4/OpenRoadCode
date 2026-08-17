# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Flask renderer for toolkit-independent OpenRoadCode menu models."""
from __future__ import annotations
from collections.abc import Mapping
from flask import Flask, abort, jsonify, redirect, render_template_string, url_for
from markupsafe import Markup
from frontends.web.screen_catalog import WebScreen, create_web_screens
from ui.menu import MenuPage

STYLE = """
body{margin:0;background:#0b0d10;color:#f5f7f8;font-family:system-ui,sans-serif}header{position:sticky;top:0;padding:14px;background:#0f1317;border-bottom:1px solid #242d35}.bar,main{max-width:900px;margin:auto}.bar{display:flex;align-items:center;gap:12px}.back{font-size:28px;color:white;text-decoration:none;border:1px solid #34424f;border-radius:10px;padding:2px 14px}.heading{flex:1}.title{font-size:24px;font-weight:800}.subtitle{color:#aebac4;font-size:13px}.grid,.gauges,.stat-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.tile,.card,.stat{padding:18px;border:1px solid #34424f;border-radius:16px;background:#151a20;color:white;text-decoration:none}.tile{min-height:100px;display:flex;flex-direction:column;justify-content:center;border-top:4px solid #5aa9e6}.tile-title{font-weight:800}.tile-subtitle,.tile-detail,.card p,.notice{color:#aebac4;margin-top:7px}.tile-detail{font-size:12px}main{padding:18px 14px}.hero-value{text-align:center;font-size:64px;font-weight:900;padding:30px 0}.hero-value small{font-size:14px;color:#aebac4}.controls{display:flex;justify-content:center;gap:12px;margin:18px 0}button{min-height:50px;padding:0 20px;border:1px solid #34424f;border-radius:14px;background:#1b2229;color:white;font-weight:800}.primary{background:#24679b}.gauge{aspect-ratio:1;border:7px solid #303b45;border-top-color:#c83232;border-radius:50%;background:#f5f5f5;color:#111;display:flex;flex-direction:column;align-items:center;justify-content:center}.gauge span{font-size:32px;font-weight:900}.gauge small,.stat small{font-size:11px}.stat{text-align:center}.stat b{display:block;font-size:22px}.forecast{display:grid;gap:10px}.forecast div{display:grid;grid-template-columns:60px 70px 1fr;padding:16px;border:1px solid #34424f;border-radius:14px;background:#151a20}.forecast span{font-size:22px;font-weight:800}.forecast small{color:#aebac4}.card{margin-bottom:14px}.card label{display:block;margin:10px 0;font-weight:700}input[type=range],.search{width:100%;box-sizing:border-box}.search{min-height:48px;padding:10px;background:#0b0d10;color:white;border:1px solid #34424f;border-radius:10px}.wide{width:100%;margin-top:12px}.album{width:150px;aspect-ratio:1;margin:20px auto;background:#222b34;border-radius:20px;display:grid;place-items:center;font-size:60px}.center{text-align:center}@media(min-width:700px){.grid{grid-template-columns:repeat(3,1fr)}.gauges{grid-template-columns:repeat(4,1fr)}}
"""
PAGE = """<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><style>{{style}}</style><header><div class=bar>{% if page_key != root %}<a class=back href='{{url_for("menu_page",page_key=root)}}'>‹</a>{% endif %}<div class=heading><div class=title>{{page.title}}</div><div class=subtitle>OpenRoadCode Web</div></div></div></header><main><div class=grid>{% for t in page.tiles %}<a class=tile href='{{url_for("select_tile",page_key=page_key,tile_key=t.key)}}'><div class=tile-title>{{t.title}}</div><div class=tile-subtitle>{{t.subtitle}}</div><div class=tile-detail>{{t.detail}}</div></a>{% endfor %}</div></main>"""
SCREEN = """<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'><style>{{style}}</style><header><div class=bar><a class=back href='{{back}}'>‹</a><div class=heading><div class=title>{{screen.title}}</div><div class=subtitle>{{screen.subtitle}}</div></div></div></header><main>{{body}}</main>"""

def create_web_frontend(pages: Mapping[str, MenuPage], *, root_page: str="main", screens: Mapping[str, WebScreen]|None=None) -> Flask:
    if root_page not in pages: raise ValueError(f"Unknown root page: {root_page}")
    screen_map=dict(screens or create_web_screens())
    app=Flask(__name__)
    @app.get("/")
    def index(): return redirect(url_for("menu_page",page_key=root_page))
    @app.get("/menu/<page_key>")
    def menu_page(page_key:str):
        page=pages.get(page_key)
        if page is None: abort(404)
        return render_template_string(PAGE,page=page,page_key=page_key,root=root_page,style=STYLE)
    @app.get("/menu/<page_key>/<tile_key>")
    def select_tile(page_key:str,tile_key:str):
        page=pages.get(page_key)
        if page is None: abort(404)
        tile=next((x for x in page.tiles if x.key==tile_key),None)
        if tile is None: abort(404)
        if tile.key in pages: return redirect(url_for("menu_page",page_key=tile.key))
        screen=screen_map.get(tile.key)
        if screen is None: abort(404)
        return render_template_string(SCREEN,screen=screen,body=Markup(screen.body_html),back=url_for("menu_page",page_key=page_key),style=STYLE)
    @app.get("/healthz")
    def healthz(): return jsonify(status="ok",frontend="web",screens=len(screen_map))
    return app
