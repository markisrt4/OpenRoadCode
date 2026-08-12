# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from __future__ import annotations

import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from controllers.image.image_cache import ImageCache
from controllers.image.image_downloader import DownloadedImage


class _Downloader:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.calls = 0

    def download(self, url: str) -> DownloadedImage:
        self.calls += 1
        return DownloadedImage(url=url, data=self.data)


class ImageCacheDiskTest(unittest.TestCase):
    def test_persistent_cache_is_reused_by_a_new_instance(self) -> None:
        output = io.BytesIO()
        Image.new("RGB", (8, 8), "#336699").save(output, format="PNG")
        downloader = _Downloader(output.getvalue())

        with TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            first = ImageCache(
                downloader=downloader,
                cache_directory=directory,
            )
            image = first.get("https://example.test/cover.png")
            image.close()
            first.clear()

            second = ImageCache(
                downloader=downloader,
                cache_directory=directory,
            )
            image = second.get("https://example.test/cover.png")
            image.close()

            self.assertEqual(1, downloader.calls)
            self.assertEqual(1, len(tuple(directory.glob("*.image"))))


if __name__ == "__main__":
    unittest.main()
