"""Presentation data for an artist's sourced profile."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArtistProfile:
    """A short artist biography and optional credited portrait."""

    name: str
    biography: str
    source_url: str
    portrait: bytes | None = None
    portrait_credit: str = ""
    portrait_url: str = ""
