# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Flask routes for the shared music-lighting controller."""
from __future__ import annotations

from flask import Flask, jsonify, request

from .music_lighting_session import WebMusicLightingSession


def register_music_lighting_routes(app: Flask, session: WebMusicLightingSession) -> None:
    @app.get("/api/music-lighting/state")
    def music_lighting_state():
        return jsonify(session.state())

    @app.post("/api/music-lighting/command")
    def music_lighting_command():
        payload = request.get_json(silent=False) or {}
        try:
            return jsonify(session.command(str(payload.get("command", "")), payload.get("value")))
        except (TypeError, ValueError) as exc:
            return jsonify(error=str(exc)), 400
