# SPDX-License-Identifier: MIT

"""Artwork variants stay small without closing the shared cached source."""

import io
from unittest.mock import Mock

from PIL import Image
import pytest

from apps.common.spotify_presentation_factory import cached_artwork_loader
from controllers.image import ImageCache
from controllers.image.image_downloader import DownloadedImage


@pytest.mark.parametrize("limit", [56, 64, 1024])
def test_encoded_variant_preserves_cache_ownership_and_size(limit):
    source = Image.new("RGB", (192, 128), "green")
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")
    source.close()
    downloader = Mock()
    downloader.download.return_value = DownloadedImage("https://example.org/art", buffer.getvalue(), "image/png")
    cache = ImageCache(downloader)
    try:
        load = cached_artwork_loader(cache, max_size=limit)
        payload = load("https://example.org/art")
        with Image.open(io.BytesIO(payload)) as decoded:
            assert max(decoded.size) <= limit
            assert decoded.getpixel((0, 0))[:3] == (0, 128, 0)
        # Encoding closes the caller-owned copy; the cached variant remains reusable.
        again = load("https://example.org/art")
        assert again == payload
        downloader.download.assert_called_once_with("https://example.org/art")
    finally:
        cache.clear()
