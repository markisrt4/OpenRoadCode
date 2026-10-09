"""Install an integrity-checked Cesium SDK without Node or runtime downloads."""

import base64
import hashlib
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryDirectory
import urllib.request

from apps.launchers.cesium_sdk import INTEGRITY, TARBALL, VERSION, sdk_directory, require_sdk


def install(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="cesium-install-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        archive = staging / "cesium.tgz"
        with urllib.request.urlopen(TARBALL, timeout=60) as response, archive.open("wb") as output:
            shutil.copyfileobj(response, output)
        with archive.open("rb") as source:
            digest = base64.b64encode(hashlib.file_digest(source, "sha512").digest()).decode()
        if "sha512-" + digest != INTEGRITY:
            raise RuntimeError("Cesium download failed integrity verification")
        with tarfile.open(archive) as bundle:
            # Only SDK assets and license files, never install scripts or symlinks.
            for member in bundle.getmembers():
                name = Path(member.name)
                if name.is_absolute() or ".." in name.parts or name.parts[0] != "package":
                    raise RuntimeError("Unsafe Cesium archive path")
                if not (member.isfile() or member.isdir()):
                    raise RuntimeError("Unsupported Cesium archive entry")
                if member.name.startswith("package/Build/Cesium/") or member.name in (
                        "package/LICENSE.md", "package/ThirdParty.json", "package/package.json"):
                    bundle.extract(member, staging, filter="data")
        prepared = staging / "package"
        require_sdk(prepared / "Build/Cesium")
        if destination.exists():
            raise RuntimeError(f"Destination already exists: {destination}")
        prepared.rename(destination)


def main():
    destination = sdk_directory().parent.parent
    if destination.exists():
        require_sdk(sdk_directory())
        print(f"Cesium {VERSION} already installed: {destination}")
    else:
        install(destination)
        print(f"Installed Cesium {VERSION}: {destination}")


if __name__ == "__main__":
    main()
