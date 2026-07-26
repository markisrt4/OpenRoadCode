from __future__ import annotations

import unittest

from PIL import Image

from apps.carUi.panels.spotify_panel import (
    album_art_accent,
    prepare_album_background,
)


class SpotifyAlbumBackgroundTest(unittest.TestCase):
    def test_resizes_and_darkens_album_artwork(self) -> None:
        source = Image.new("RGB", (300, 300), (240, 120, 60))
        try:
            background = prepare_album_background(
                source,
                width=800,
                height=360,
            )
        finally:
            source.close()

        try:
            self.assertEqual((800, 360), background.size)
            red, green, blue = background.getpixel((400, 180))
            self.assertLess(red, 100)
            self.assertLess(green, 60)
            self.assertLess(blue, 40)
        finally:
            background.close()

    def test_rejects_invalid_dimensions(self) -> None:
        source = Image.new("RGB", (10, 10))
        try:
            with self.assertRaises(ValueError):
                prepare_album_background(
                    source,
                    width=0,
                    height=100,
                )
        finally:
            source.close()

    def test_album_accent_reflects_artwork_and_remains_bright(self) -> None:
        source = Image.new("RGB", (20, 20), (15, 70, 180))
        try:
            accent = album_art_accent(source)
        finally:
            source.close()

        self.assertRegex(accent, r"^#[0-9A-F]{6}$")
        red, green, blue = (
            int(accent[index:index + 2], 16)
            for index in (1, 3, 5)
        )
        self.assertGreater(blue, red)
        self.assertGreater(blue, green)
        self.assertGreater(max(red, green, blue), 190)


if __name__ == "__main__":
    unittest.main(verbosity=2)
