"""Verify a MusicForge API endpoint and save it for desktop launches."""

import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

from common.musicforge_airplay import validate_airplay_url
from common.xdg_paths import openroadcode_config_dir


def configure_airplay(value: str) -> None:
    url = validate_airplay_url(value)
    with urlopen(f"{url}/api/v1/stations", timeout=5) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("stations"), list):
        raise ValueError("The server did not return a MusicForge station list.")
    target = openroadcode_config_dir("musicforge-airplay-url")
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as output:
        temporary = Path(output.name)
        try:
            output.write(url + "\n")
            output.close()
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "Usage: python3 -m scripts.installers.setup_musicforge_airplay API_URL", file=sys.stderr
        )
        return 2
    try:
        configure_airplay(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"MusicForge setup failed: {exc}", file=sys.stderr)
        return 1
    print("MusicForge API verified and saved for ORC.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
