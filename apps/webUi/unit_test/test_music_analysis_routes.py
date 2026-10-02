# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""HTTP contract tests for shared music analysis and source selection."""
import struct

from flask import Flask

from apps.webUi.music_analysis_routes import create_music_analysis_routes
from controllers.audio.music_analysis.music_analysis_session import MusicAnalysisSession, PushAudioCapture


def test_source_discovery_selection_pcm_and_calibration():
    session = MusicAnalysisSession({"browser": PushAudioCapture, "android-test": PushAudioCapture})
    app = Flask(__name__)
    app.register_blueprint(create_music_analysis_routes(session))
    client = app.test_client()

    result = client.get("/api/audio-analysis/sources")
    assert result.status_code == 200
    assert result.json["sources"] == ["browser", "android-test"]
    assert result.json["state"]["source"] is None

    assert client.post("/api/audio-analysis/source", json={"source": "missing"}).status_code == 400
    assert client.post("/api/audio-analysis/source", json={"source": 12}).status_code == 400
    assert client.post("/api/audio-analysis/source", json={"source": "browser", "running": "yes"}).status_code == 400
    assert client.post("/api/audio-analysis/zeroize/start").status_code == 400

    result = client.post("/api/audio-analysis/source", json={"source": "browser"})
    assert result.json["running"]
    assert result.json["source"] == "browser"
    assert client.post("/api/audio-analysis/zeroize/start").json["calibrating"]
    frame = struct.pack("<2048h", *([1000] * 2048))
    result = client.post("/api/audio-analysis/session/pcm16", data=frame,
                         headers={"X-Sample-Rate": "48000", "X-Audio-Source": "browser"})
    assert result.status_code == 200
    assert result.json["sample_rate_hz"] == 48000
    assert client.post("/api/audio-analysis/zeroize/finish").json["zeroized"]

    result = client.post("/api/audio-analysis/source", json={"source": "android-test"})
    assert result.json["running"]
    assert not result.json["zeroized"]
    assert client.post("/api/audio-analysis/session/pcm16", data=frame,
                       headers={"X-Sample-Rate": "48000", "X-Audio-Source": "browser"}).status_code == 400
    assert client.post("/api/audio-analysis/zeroize/clear").status_code == 200
    assert client.post("/api/audio-analysis/session/stop").json["running"] is False
    assert client.get("/api/audio-analysis/session/state").json["source"] == "android-test"
    assert client.post("/api/audio-analysis/zeroize/nope").status_code == 404
