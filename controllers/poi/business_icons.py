# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Resolve approved bundled PNGs; no runtime network or arbitrary file access."""
import base64
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import struct

DIRECTORY = Path(__file__).with_name('catalog') / 'icons'


@lru_cache(maxsize=128)
def icon_properties(icon_id: str | None) -> dict[str, str]:
    if not icon_id or not re.fullmatch(r'[a-z0-9-]{1,64}', icon_id):
        return {}
    try:
        manifest = json.loads((DIRECTORY / 'manifest.json').read_text())
        if manifest['schema_version'] != 1:
            return {}
        entry = manifest['icons'][icon_id]
        if entry['file'] != icon_id + '.png':
            return {}
        data = (DIRECTORY / entry['file']).read_bytes()
        if (len(data) > 65536 or data[:8] != b'\x89PNG\r\n\x1a\n'
                or len(data) < 24 or struct.unpack('>II', data[16:24]) != (64, 64)
                or hashlib.sha256(data).hexdigest() != entry['sha256']):
            return {}
        return {'brand_icon': 'business:' + icon_id, 'brand_icon_png': base64.b64encode(data).decode('ascii')}
    except (OSError, ValueError, KeyError, TypeError):
        return {}
