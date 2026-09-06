# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Small dependency-free Chrome DevTools Protocol client helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DevToolsTarget:
    id: str
    title: str
    url: str
    web_socket_debugger_url: str


class ChromiumDevToolsClient:
    """Use Chromium's local DevTools endpoint for discovery and page commands."""

    _WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, *, host: str = "127.0.0.1", port: int = 9223, timeout_seconds: float = 1.0) -> None:
        self._base_url = f"http://{host}:{port}"
        self._timeout_seconds = timeout_seconds
        self._next_command_id = 1

    def targets(self) -> tuple[DevToolsTarget, ...]:
        payload = self._json_get("/json/list")
        if not isinstance(payload, list):
            return ()
        return tuple(
            DevToolsTarget(
                id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                url=str(item.get("url", "")),
                web_socket_debugger_url=str(item.get("webSocketDebuggerUrl", "")),
            )
            for item in payload
            if item.get("type") == "page" and item.get("id")
        )

    def earth_target(self) -> DevToolsTarget | None:
        for target in self.targets():
            if "earth.google.com" in target.url:
                return target
        return None

    def activate(self, target_id: str) -> bool:
        encoded = urllib.parse.quote(target_id, safe="")
        try:
            self._json_get(f"/json/activate/{encoded}")
            return True
        except (OSError, ValueError):
            return False

    def version(self) -> dict[str, Any]:
        payload = self._json_get("/json/version")
        return payload if isinstance(payload, dict) else {}

    def command(
        self,
        target: DevToolsTarget,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send one Chrome DevTools Protocol command to a page target."""
        if not target.web_socket_debugger_url:
            raise ValueError("DevTools target does not expose a WebSocket debugger URL")
        return self._command(target.web_socket_debugger_url, method, params or {})

    def command_earth(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send one Chrome DevTools Protocol command to the Google Earth page."""
        target = self.earth_target()
        if target is None:
            raise RuntimeError("Google Earth DevTools target is not available")
        return self.command(target, method, params)

    def set_geolocation_override(
        self,
        latitude: float,
        longitude: float,
        *,
        accuracy_m: float = 5.0,
    ) -> None:
        """Override browser geolocation for the running Google Earth page."""
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90 degrees")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180 degrees")
        if accuracy_m < 0.0:
            raise ValueError("accuracy_m must be non-negative")
        self.command_earth(
            "Emulation.setGeolocationOverride",
            {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "accuracy": float(accuracy_m),
            },
        )

    def clear_geolocation_override(self) -> None:
        """Restore normal browser geolocation behavior for Google Earth."""
        self.command_earth("Emulation.clearGeolocationOverride")

    def evaluate(self, target: DevToolsTarget, expression: str, *, return_by_value: bool = True) -> Any:
        """Evaluate JavaScript in a page target through the CDP WebSocket."""
        result = self.command(
            target,
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": return_by_value,
                "awaitPromise": True,
            },
        )
        exception = result.get("exceptionDetails")
        if exception:
            text = str(exception.get("text") or "JavaScript evaluation failed")
            raise RuntimeError(text)
        remote = result.get("result", {})
        if "value" in remote:
            return remote["value"]
        return remote.get("description")

    def evaluate_earth(self, expression: str, *, return_by_value: bool = True) -> Any:
        """Evaluate JavaScript in the currently running Google Earth page."""
        target = self.earth_target()
        if target is None:
            raise RuntimeError("Google Earth DevTools target is not available")
        return self.evaluate(target, expression, return_by_value=return_by_value)

    def _command(self, web_socket_url: str, method: str, params: dict[str, Any]) -> dict[str, Any]:
        command_id = self._next_command_id
        self._next_command_id += 1
        payload = json.dumps({"id": command_id, "method": method, "params": params}, separators=(",", ":"))
        with self._connect_websocket(web_socket_url) as connection:
            self._send_text(connection, payload)
            while True:
                message = self._receive_text(connection)
                decoded = json.loads(message)
                if decoded.get("id") != command_id:
                    continue
                if "error" in decoded:
                    error = decoded["error"]
                    raise RuntimeError(str(error.get("message") or error))
                result = decoded.get("result", {})
                return result if isinstance(result, dict) else {}

    def _connect_websocket(self, web_socket_url: str) -> socket.socket:
        parsed = urllib.parse.urlsplit(web_socket_url)
        if parsed.scheme != "ws":
            raise ValueError(f"Unsupported DevTools WebSocket scheme: {parsed.scheme}")
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        path = urllib.parse.urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        connection = socket.create_connection((host, port), timeout=self._timeout_seconds)
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        connection.sendall(request.encode("ascii"))
        response = self._receive_http_headers(connection)
        status_line = response.split("\r\n", 1)[0]
        if " 101 " not in status_line:
            connection.close()
            raise ConnectionError(f"DevTools WebSocket handshake failed: {status_line}")
        headers = {}
        for line in response.split("\r\n")[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        expected = base64.b64encode(
            hashlib.sha1((key + self._WEBSOCKET_GUID).encode("ascii")).digest()
        ).decode("ascii")
        if headers.get("sec-websocket-accept") != expected:
            connection.close()
            raise ConnectionError("DevTools WebSocket handshake returned an invalid accept key")
        return connection

    @staticmethod
    def _receive_http_headers(connection: socket.socket) -> str:
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = connection.recv(4096)
            if not chunk:
                raise ConnectionError("DevTools WebSocket closed during handshake")
            data.extend(chunk)
            if len(data) > 65536:
                raise ConnectionError("DevTools WebSocket handshake headers are too large")
        return bytes(data).split(b"\r\n\r\n", 1)[0].decode("iso-8859-1")

    @staticmethod
    def _send_text(connection: socket.socket, text: str) -> None:
        payload = text.encode("utf-8")
        mask = os.urandom(4)
        length = len(payload)
        frame = bytearray([0x81])
        if length < 126:
            frame.append(0x80 | length)
        elif length <= 0xFFFF:
            frame.append(0x80 | 126)
            frame.extend(struct.pack("!H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack("!Q", length))
        frame.extend(mask)
        frame.extend(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        connection.sendall(frame)

    def _receive_text(self, connection: socket.socket) -> str:
        fragments = bytearray()
        while True:
            first, second = self._recv_exact(connection, 2)
            fin = bool(first & 0x80)
            opcode = first & 0x0F
            masked = bool(second & 0x80)
            length = second & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(connection, 2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(connection, 8))[0]
            mask = self._recv_exact(connection, 4) if masked else b""
            payload = bytearray(self._recv_exact(connection, length))
            if masked:
                for index in range(len(payload)):
                    payload[index] ^= mask[index % 4]
            if opcode == 0x8:
                raise ConnectionError("DevTools WebSocket closed")
            if opcode == 0x9:
                self._send_control(connection, 0xA, bytes(payload))
                continue
            if opcode not in (0x0, 0x1):
                continue
            fragments.extend(payload)
            if fin:
                return fragments.decode("utf-8")

    @staticmethod
    def _send_control(connection: socket.socket, opcode: int, payload: bytes) -> None:
        mask = os.urandom(4)
        frame = bytearray([0x80 | opcode, 0x80 | len(payload)])
        frame.extend(mask)
        frame.extend(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        connection.sendall(frame)

    @staticmethod
    def _recv_exact(connection: socket.socket, count: int) -> bytes:
        data = bytearray()
        while len(data) < count:
            chunk = connection.recv(count - len(data))
            if not chunk:
                raise ConnectionError("DevTools WebSocket closed unexpectedly")
            data.extend(chunk)
        return bytes(data)

    def _json_get(self, path: str) -> Any:
        request = urllib.request.Request(self._base_url + path, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
            return json.load(response)
