# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

"""Prepare a writable Termux copy of a deployed Valhalla configuration."""

import argparse
import json
from pathlib import Path


LINUX_DATA_ROOTS = ("/data/valhalla/", "/srv/openroadcode/valhalla/", "/output/valhalla/")


def prepare(source: Path, destination: Path, data_root: Path, runtime_root: Path) -> None:
    """Relocate standard deployment paths without changing the source configuration."""
    config = json.loads(source.read_text())
    if not isinstance(config, dict) or not isinstance(config.get("mjolnir"), dict):
        raise ValueError("Valhalla configuration must contain a mjolnir object")
    runtime_root.mkdir(parents=True, exist_ok=True)

    def relocate(value):
        if isinstance(value, dict):
            return {key: relocate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [relocate(item) for item in value]
        if isinstance(value, str):
            if value.startswith("ipc:///tmp/"):
                return "ipc://" + str(runtime_root / value.removeprefix("ipc:///tmp/"))
            for prefix in LINUX_DATA_ROOTS:
                if value.startswith(prefix):
                    return str(data_root / value.removeprefix(prefix))
        return value

    config = relocate(config)
    # Builder output can contain arbitrary build-machine paths. The four
    # standard installed artifacts take precedence when present locally.
    for key, name in (("tile_dir", "tiles"), ("tile_extract", "tiles.tar"),
                      ("admin", "admins.sqlite"), ("timezone", "timezones.sqlite")):
        path = data_root / name
        if path.exists():
            config["mjolnir"][key] = str(path)
    logging = config.setdefault("logging", {})
    if logging.get("type") == "file" and str(logging.get("file_name", "")).startswith(("/tmp/", "/var/log/")):
        logging["file_name"] = str(runtime_root / Path(logging["file_name"]).name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "destination", "data-root", "runtime-root"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    try:
        prepare(args.source, args.destination, args.data_root, args.runtime_root)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot prepare Termux Valhalla configuration: {error}\n")


if __name__ == "__main__":
    main()
