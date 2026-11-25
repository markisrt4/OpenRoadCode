# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

import io
import subprocess
import sys
import tarfile

import pytest

from scripts.runtime import download_navigation_release as release


def test_checksums(tmp_path):
    checksums = tmp_path / "SHA256SUMS"
    digest = "a" * 64
    checksums.write_text(f"{digest}  part-0000\n")
    assert release.parse_checksums(checksums, ["part-0000"]) == {"part-0000": digest}


@pytest.mark.parametrize("name", ["../escape", "unexpected", "part-0000\ninvalid"])
def test_unexpected_checksums(tmp_path, name):
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text(f"{'a' * 64}  {name}\n")
    with pytest.raises(ValueError):
        release.parse_checksums(checksums, ["part-0000"])


def test_missing_checksum(tmp_path):
    checksums = tmp_path / "SHA256SUMS"
    checksums.write_text("")
    with pytest.raises(ValueError, match="incomplete"):
        release.parse_checksums(checksums, ["part-0000"])


def test_cached_download(tmp_path, monkeypatch):
    path = tmp_path / "part"
    path.write_bytes(b"cached")

    def unexpected(*args, **kwargs):
        pytest.fail("Valid cached asset must not be downloaded again")

    monkeypatch.setattr(release.subprocess, "run", unexpected)
    release.download("unused", path, release.digest(path))


def test_bad_download(tmp_path, monkeypatch):
    path = tmp_path / "part"

    def fake_download(*args, **kwargs):
        path.with_suffix(".partial").write_bytes(b"corrupt")

    monkeypatch.setattr(release.subprocess, "run", fake_download)
    with pytest.raises(ValueError, match="Checksum mismatch"):
        release.download("unused", path, "a" * 64)
    assert not path.exists()
    assert not path.with_suffix(".partial").exists()


def make_archive(path, name):
    payload = b"test data"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo(name)
        member.size = len(payload)
        archive.addfile(member, io.BytesIO(payload))


def test_split_archive(tmp_path):
    archive = tmp_path / "archive.gz"
    make_archive(archive, "maps/test")
    data = archive.read_bytes()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.write_bytes(data[:20])
    second.write_bytes(data[20:])
    stage = tmp_path / "stage"
    release.extract([first, second], stage)
    assert (stage / "maps/test").read_bytes() == b"test data"


def test_traversal_rejected(tmp_path):
    archive = tmp_path / "archive.gz"
    make_archive(archive, "../escape")
    stage = tmp_path / "stage"
    with pytest.raises(tarfile.FilterError):
        release.extract([archive], stage)
    assert not stage.exists()
    assert not (tmp_path / "escape").exists()


def test_existing_stage_preserved(tmp_path):
    stage = tmp_path / "stage"
    stage.mkdir()
    marker = stage / "marker"
    marker.touch()
    with pytest.raises(ValueError):
        release.extract([], stage)
    assert marker.exists()


def test_manifest_only(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    stage = tmp_path / "stage"
    requested = []
    manifest = b'{"generated_unix": 1}'

    def fake_download(url, path, expected=None):
        requested.append(path.name)
        if path.name == "SHA256SUMS":
            path.write_text(
                f"{'a' * 64}  navigation-data.tar.gz.part-0000\n{'b' * 64}  build-manifest.json\n"
            )
        elif path.name == "build-manifest.json":
            path.write_bytes(manifest)
        else:
            pytest.fail("Manifest-only mode requested an archive part")

    monkeypatch.setattr(release, "download", fake_download)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "download_navigation_release",
            "--region",
            "us/michigan",
            "--cache",
            str(cache),
            "--stage",
            str(stage),
            "--manifest-only",
        ],
    )
    release.main()
    assert requested == ["SHA256SUMS", "build-manifest.json"]
    assert (stage / "build-manifest.json").read_bytes() == manifest


def test_interrupted_download_resumes(tmp_path, monkeypatch):
    path = tmp_path / "part"
    partial = path.with_suffix(".partial")
    payload = b"complete payload"
    reference = tmp_path / "reference"
    reference.write_bytes(payload)
    expected = release.digest(reference)

    def interrupted(command, **kwargs):
        partial.write_bytes(payload[:5])
        raise subprocess.CalledProcessError(18, command)

    monkeypatch.setattr(release.subprocess, "run", interrupted)
    with pytest.raises(subprocess.CalledProcessError):
        release.download("unused", path, expected)
    assert partial.read_bytes() == payload[:5]
    assert not path.exists()

    def resumed(command, **kwargs):
        assert command[command.index("--continue-at") + 1] == "-"
        assert partial.read_bytes() == payload[:5]
        with partial.open("ab") as stream:
            stream.write(payload[5:])

    monkeypatch.setattr(release.subprocess, "run", resumed)
    release.download("unused", path, expected)
    assert path.read_bytes() == payload
    assert not partial.exists()
