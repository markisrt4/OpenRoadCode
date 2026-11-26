"""Persistent RF receiver preferences; does not acquire hardware."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from common.xdg_paths import openroadcode_config_dir
from hardware_io.rf.receiver_discovery_if import ReceiverDevice, ReceiverDiscoveryIf


@dataclass(frozen=True, slots=True)
class ReceiverAssignments:
    radio: str | None = None
    weather: str | None = None
    adsb: str | None = None

    def __post_init__(self) -> None:
        for value in (self.radio, self.weather, self.adsb):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError("Receiver identity must be a nonempty string or null")


class ReceiverAssignmentStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or openroadcode_config_dir("rf-receivers.json")

    def load(self) -> ReceiverAssignments:
        try:
            data = json.loads(self.path.read_text())
        except FileNotFoundError:
            return ReceiverAssignments()
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("Unsupported RF receiver configuration")
        return ReceiverAssignments(**data["assignments"])

    def save(self, assignments: ReceiverAssignments) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump({"version": 1, "assignments": asdict(assignments)}, stream, indent=2)
                stream.write("\n")
            os.replace(name, self.path)
        finally:
            Path(name).unlink(missing_ok=True)


class ReceiverAssignmentController:
    def __init__(self, discovery: ReceiverDiscoveryIf) -> None:
        self._discovery = discovery

    def resolve(self, assignments: ReceiverAssignments) -> dict[str, ReceiverDevice | None]:
        devices = self._discovery.discover()
        result = {}
        for role, identity in asdict(assignments).items():
            matches = [device for device in devices if identity and device.identity == identity]
            result[role] = matches[0] if len(matches) == 1 else None
        return result
