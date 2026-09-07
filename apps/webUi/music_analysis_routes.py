# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Source-independent WebUI music analysis HTTP transport."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession


def create_music_analysis_routes(session: MusicAnalysisSession) -> Blueprint:
    """Expose source discovery, lifecycle, PCM ingress, and calibration."""
    api = Blueprint("music_analysis", __name__)

    def error(exc: Exception):
        return jsonify(error=str(exc)), 400 if isinstance(exc, (ValueError, RuntimeError)) else 502

    @api.get("/api/audio-analysis/sources")
    def sources():
        return jsonify(sources=list(session.sources()), state=session.state())

    @api.get("/api/audio-analysis/session/state")
    def state():
        return jsonify(session.state())

    @api.post("/api/audio-analysis/source")
    def select_source():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or not isinstance(payload.get("source"), str):
            return jsonify(error="source must be a string"), 400
        if not isinstance(payload.get("running", True), bool):
            return jsonify(error="running must be a boolean"), 400
        try:
            source = payload["source"]
            if payload.get("running", True):
                result = session.start(source)
            else:
                result = session.select(source)
            return jsonify(result)
        except Exception as exc:
            return error(exc)

    @api.post("/api/audio-analysis/session/stop")
    def stop():
        try:
            return jsonify(session.stop())
        except Exception as exc:
            return error(exc)

    @api.post("/api/audio-analysis/session/pcm16")
    def pcm16():
        try:
            source = request.headers.get("X-Audio-Source", "browser")
            rate = int(request.headers.get("X-Sample-Rate", "0"))
            return jsonify(session.push_pcm16(request.get_data(), rate, source=source))
        except Exception as exc:
            return error(exc)

    @api.post("/api/audio-analysis/zeroize/<action>")
    def zeroize(action: str):
        commands = {
            "start": session.start_zeroize,
            "finish": session.finish_zeroize,
            "clear": session.clear_zeroize,
        }
        if action not in commands:
            return jsonify(error="Unknown calibration command"), 404
        try:
            return jsonify(commands[action]())
        except Exception as exc:
            return error(exc)

    return api
