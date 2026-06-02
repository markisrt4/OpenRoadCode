from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from config.radio_config_manager import RADIO_CONFIG_DIR


@dataclass(frozen=True)
class RadioConfigManifestEntry:
    key: str
    config_path: Path


@dataclass(frozen=True)
class RadioManifest:
    radio_configs: list[RadioConfigManifestEntry]
    scanner_bands: list[RadioConfigManifestEntry]


class RadioManifestParser:
    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)

    def load(self) -> RadioManifest:
        with self.manifest_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return RadioManifest(
            radio_configs=self._parse_config_group(data.get("radio_configs", {})),
            scanner_bands=self._parse_config_group(data.get("scanner_bands", {})),
        )

    def _parse_config_group(
        self,
        items: dict[str, str],
    ) -> list[RadioConfigManifestEntry]:
        entries: list[RadioConfigManifestEntry] = []

        for key, filename in items.items():
            entries.append(
                RadioConfigManifestEntry(
                    key=key,
                    config_path=RADIO_CONFIG_DIR / filename,
                )
            )

        return entries
