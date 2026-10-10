#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the SMS Service Manager integration to the current feature checkout.

Run once from the repository root. Fails rather than guessing if source changes.
"""
from pathlib import Path

def edit(path, replacements):
    file = Path(path)
    source = file.read_text()
    for old, new in replacements:
        if new in source:
            continue
        if source.count(old) != 1:
            raise SystemExit(f"Expected exactly one insertion point in {path}: {old!r}")
        source = source.replace(old, new, 1)
    file.write_text(source)

edit("services/termux/service_manager_http.py", [
    (
        "from services.common.service_manager_sms_proxy import serve_sms\n",
        "from services.common.service_manager_sms_proxy import serve_sms\n"
        "from services.common.service_manager_sms_provision import serve_sms_provision\n",
    ),
    (
        '        if serve_sms(self, "GET"):\n',
        '        if serve_sms_provision(self, "GET"):\n'
        '            return\n'
        '        if serve_sms(self, "GET"):\n',
    ),
    (
        '        if serve_sms(self, "POST"):\n',
        '        if serve_sms_provision(self, "POST"):\n'
        '            return\n'
        '        if serve_sms(self, "POST"):\n',
    ),
    (
        '    def _browser_pairing_start(self) -> None:\n',
        '    def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API\n'
        '        if serve_sms_provision(self, "DELETE"):\n'
        '            return\n'
        '        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})\n\n'
        '    def _browser_pairing_start(self) -> None:\n',
    ),
])
edit("services/common/service_manager_sms_proxy.py", [
    (
        "from services.common.service_manager_messaging_auth import messaging_authorized\n",
        "from services.common.service_manager_messaging_auth import messaging_authorized\n"
        "from services.common.service_manager_sms_credentials import load_token\n",
    ),
    (
        '    internal_token = os.environ.get(ANDROID_TOKEN_ENV, "").strip() or None\n',
        '    internal_token = os.environ.get(ANDROID_TOKEN_ENV, "").strip() or load_token()\n',
    ),
])
print("SMS provisioning routes and private credential fallback integrated.")
