"""Compatibility name for the BMP390 sensor."""

from .bmp3xx import Bmp3xx


class Bmp390(Bmp3xx):
    """BMP390-compatible name for the shared BMP3XX implementation."""
