"""Compatibility name for the BMP388 sensor."""

from .bmp3xx import Bmp3xx


class Bmp388(Bmp3xx):
    """BMP388-compatible name for the shared BMP3XX implementation."""
