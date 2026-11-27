"""Resolve optional UI features before importing subsystem composition."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass

FEATURES = ("camera", "audio", "native_map", "spotify", "opengl")


@dataclass(frozen=True, slots=True)
class RuntimeFeatures:
    """Effective startup feature selection."""

    camera: bool
    audio: bool
    native_map: bool
    spotify: bool
    opengl: bool

    @classmethod
    def resolve(cls, args: argparse.Namespace, environment: Mapping[str, str]) -> RuntimeFeatures:
        simulation = args.simulation or environment.get("ORC_SIMULATION") == "1"

        def enabled(feature: str) -> bool:
            explicit = getattr(args, feature)
            if explicit is not None:
                return bool(explicit)
            if simulation:
                return False
            return environment.get(f"ORC_NO_{feature.upper()}") != "1"

        return cls(*(enabled(feature) for feature in FEATURES))

    def apply(self, environment: MutableMapping[str, str]) -> None:
        """Publish compatibility flags for existing subsystem adapters."""
        for feature in FEATURES:
            environment[f"ORC_NO_{feature.upper()}"] = "0" if getattr(self, feature) else "1"


def add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    """Register positive and negative runtime feature overrides."""
    parser.add_argument("--simulation", action="store_true", help="Use lightweight runtime defaults")
    for feature in FEATURES:
        parser.add_argument(
            f"--{feature.replace('_', '-')}", action=argparse.BooleanOptionalAction, default=None
        )
