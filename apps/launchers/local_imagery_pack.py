"""Load a checked local image and immutable coverage, outside web presentation."""

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

from common.xdg_paths import openroadcode_data_dir
from ui.navigation.local_imagery_state import LocalImageryState


def detroit_pack_directory():
    return openroadcode_data_dir("map-packs", "detroit-imagery-v1")


@dataclass(frozen=True, slots=True)
class LocalImageryPack:
    """Native storage handle paired with a toolkit-independent layer snapshot."""

    state: LocalImageryState
    image: Path

    @classmethod
    def load(cls, directory):
        root = Path(directory).resolve()
        manifest = json.loads((root / "manifest.json").read_text())
        if manifest.get("schema") != 1:
            raise ValueError("Unsupported imagery-pack schema")
        image = (root / manifest["image"]).resolve()
        if not image.is_relative_to(root) or not image.is_file():
            raise ValueError("Imagery file must be inside the pack")
        if image.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Prototype imagery exceeds 20 MB limit")
        with image.open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != manifest["sha256"]:
            raise ValueError("Imagery checksum does not match the manifest")
        west, south, east, north = manifest["bounds_deg"]
        state = LocalImageryState(manifest["title"], manifest["attribution"],
                                  *(math.radians(v) for v in (west, south, east, north)))
        return cls(state, image)
