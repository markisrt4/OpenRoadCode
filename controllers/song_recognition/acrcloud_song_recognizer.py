# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""ACRCloud implementation of :class:`SongRecognitionIf`."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .song_recognition_if import SongRecognitionIf, SongRecognitionResult


@dataclass(frozen=True)
class AcrCloudConfig:
    host: str
    access_key: str
    access_secret: str
    timeout_seconds: float = 10.0


class AcrCloudSongRecognizer(SongRecognitionIf):
    """Recognize short audio clips using ACRCloud's identification API."""

    def __init__(self, config: AcrCloudConfig) -> None:
        self._config = config

    def recognize(self, audio: bytes, *, sample_bytes: int | None = None) -> SongRecognitionResult | None:
        if not audio:
            return None

        timestamp = str(int(time.time()))
        method = "POST"
        uri = "/v1/identify"
        data_type = "audio"
        signature_version = "1"
        string_to_sign = "\n".join(
            (method, uri, self._config.access_key, data_type, signature_version, timestamp)
        )
        digest = hmac.new(
            self._config.access_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(digest).decode("ascii")

        boundary = f"----OpenRoadCode{int(time.time() * 1000)}"
        fields = {
            "access_key": self._config.access_key,
            "data_type": data_type,
            "signature_version": signature_version,
            "signature": signature,
            "sample_bytes": str(sample_bytes if sample_bytes is not None else len(audio)),
            "timestamp": timestamp,
        }
        body = self._multipart(boundary, fields, audio)
        host = self._config.host.removeprefix("https://").removeprefix("http://").rstrip("/")
        request = urllib.request.Request(
            f"https://{host}{uri}",
            data=body,
            method=method,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"ACRCloud recognition request failed: {exc}") from exc

        status = payload.get("status", {})
        if status.get("code") != 0:
            if status.get("code") == 1001:  # No result.
                return None
            raise RuntimeError(f"ACRCloud error {status.get('code')}: {status.get('msg', 'unknown error')}")

        matches = payload.get("metadata", {}).get("music", [])
        if not matches:
            return None
        match = matches[0]
        artists = tuple(a.get("name", "") for a in match.get("artists", []) if a.get("name"))
        album = match.get("album") or {}
        external_ids = match.get("external_ids") or {}
        return SongRecognitionResult(
            title=match.get("title", "Unknown title"),
            artists=artists,
            album=album.get("name"),
            release_date=match.get("release_date"),
            label=match.get("label"),
            isrc=external_ids.get("isrc"),
            score=match.get("score"),
            provider="acrcloud",
            provider_track_id=match.get("acrid"),
        )

    @staticmethod
    def _multipart(boundary: str, fields: dict[str, str], audio: bytes) -> bytes:
        chunks: list[bytes] = []
        for name, value in fields.items():
            chunks.extend((
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(), b"\r\n",
            ))
        chunks.extend((
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="sample"; filename="sample.bin"\r\n',
            b"Content-Type: application/octet-stream\r\n\r\n",
            audio, b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ))
        return b"".join(chunks)
