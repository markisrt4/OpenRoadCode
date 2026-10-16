"""Reject corrupt SDKs and retain usable local assets and licenses."""

import base64
import hashlib
import io
from pathlib import Path
import tarfile

import pytest

from development.maps import install_cesium


def archive(entries):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:gz") as bundle:
        for name, content in entries.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(content)
            bundle.addfile(entry, io.BytesIO(content))
    return stream.getvalue()


def test_integrity_failure_does_not_install_sdk(tmp_path, monkeypatch):
    monkeypatch.setattr(install_cesium.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(b"wrong archive"))
    destination = tmp_path / "sdk"
    with pytest.raises(RuntimeError, match="integrity"):
        install_cesium.install(destination)
    assert not destination.exists()


def test_installer_keeps_sdk_and_licenses_but_not_package_scripts(tmp_path, monkeypatch):
    content = archive({
        "package/Build/Cesium/Cesium.js": b"sdk",
        "package/Build/Cesium/Widgets/widgets.css": b"css",
        "package/Build/Cesium/Assets/asset.txt": b"asset",
        "package/Build/Cesium/Workers/worker.js": b"worker",
        "package/LICENSE.md": b"license",
        "package/ThirdParty.json": b"{}",
        "package/install.js": b"not installed",
    })
    digest = base64.b64encode(hashlib.sha512(content).digest()).decode()
    monkeypatch.setattr(install_cesium, "INTEGRITY", "sha512-" + digest)
    monkeypatch.setattr(install_cesium.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(content))
    destination = tmp_path / "sdk"
    install_cesium.install(destination)
    assert (destination / "LICENSE.md").read_bytes() == b"license"
    assert (destination / "Build/Cesium/Cesium.js").read_bytes() == b"sdk"
    assert not (destination / "install.js").exists()
    assert not list(tmp_path.glob("cesium-install-*"))


def test_archive_cannot_write_outside_install_directory(tmp_path, monkeypatch):
    content = archive({"package/../../escape": b"bad"})
    monkeypatch.setattr(install_cesium, "INTEGRITY", "sha512-" + base64.b64encode(hashlib.sha512(content).digest()).decode())
    monkeypatch.setattr(install_cesium.urllib.request, "urlopen", lambda *a, **kw: io.BytesIO(content))
    with pytest.raises(RuntimeError, match="Unsafe"):
        install_cesium.install(tmp_path / "sdk")
    assert not (tmp_path / "escape").exists()
