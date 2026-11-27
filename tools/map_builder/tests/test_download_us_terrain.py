import hashlib
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

from development.maps import download_us_terrain as downloader
from development.maps.state_map_catalog import state_plan


def make_archive(root, payload=b"validated-transport"):
    root.mkdir(parents=True, exist_ok=True)
    region = state_plan("CO")["overview_regions"][0]
    archive = root / (region["coverage"] + "-terrain.zip")
    archive.write_bytes(payload)
    archive.with_suffix(".zip.json").write_text(
        json.dumps(
            dict(
                schema=1,
                kind="terrain",
                coverage=region["coverage"],
                archive=archive.name,
                bytes=len(payload),
                sha256=hashlib.sha256(payload).hexdigest(),
                bounds_deg=region["bounds_deg"],
            )
        )
    )
    return archive


def test_only_successful_state_jobs_are_selected():
    assert downloader.successful_states(
        [
            dict(name="us-coarse-terrain / state (CO)", conclusion="success"),
            dict(name="us-coarse-terrain / state (HI)", conclusion="failure"),
            dict(name="us-coarse-terrain / probe (AK)", conclusion="success"),
        ]
    ) == ["CO"]


def test_verified_colorado_is_reused_without_transfer(tmp_path, monkeypatch):
    original = make_archive(tmp_path / "earlier")
    run = Mock()
    monkeypatch.setattr(downloader.subprocess, "run", run)
    downloader.fetch_state("123", "CO", tmp_path / "output", [tmp_path / "earlier"])
    run.assert_not_called()
    assert (tmp_path / "output/CO" / original.name).read_bytes() == original.read_bytes()


def test_eof_retries_only_current_state_and_discards_processing(tmp_path, monkeypatch):
    calls = []

    def transfer(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, command)
        destination = Path(command[command.index("--dir") + 1])
        make_archive(destination)
        (destination / "processing").mkdir()
        (destination / "processing/intermediate.tif").write_bytes(b"not retained")

    monkeypatch.setattr(downloader.subprocess, "run", transfer)
    monkeypatch.setattr(downloader.time, "sleep", lambda _: None)
    output = tmp_path / "output"
    output.mkdir()
    downloader.fetch_state("123", "CO", output, [], attempts=2)
    assert len(calls) == 2
    assert not list(output.rglob("intermediate.tif"))
    assert len(list(output.rglob("*.zip"))) == 1


def test_tampered_archive_is_downloaded_again(tmp_path, monkeypatch):
    output = tmp_path / "output"
    archive = make_archive(output / "CO")
    archive.write_bytes(b"corrupt")
    run = Mock(
        side_effect=lambda command, **kwargs: make_archive(
            Path(command[command.index("--dir") + 1])
        )
    )
    monkeypatch.setattr(downloader.subprocess, "run", run)
    downloader.fetch_state("123", "CO", output, [])
    assert run.call_count == 1
    assert archive.read_bytes() == b"validated-transport"


def test_older_gh_pagination_without_slurp(monkeypatch):
    responses = [
        json.dumps({"jobs": [{"name": str(i)} for i in range(100)]}),
        json.dumps({"jobs": [{"name": "last"}]}),
    ]
    call = Mock(side_effect=responses)
    monkeypatch.setattr(downloader.subprocess, "check_output", call)
    result = downloader.pages("123", "jobs", "jobs")
    assert len(result) == 101
    assert result[-1]["name"] == "last"
    for args, _ in call.call_args_list:
        assert "--slurp" not in args[0]
        assert "--paginate" not in args[0]
    assert call.call_args_list[0].args[0][-1].endswith("page=1")
    assert call.call_args_list[1].args[0][-1].endswith("page=2")


def test_empty_github_listing_stops_after_one_page(monkeypatch):
    call = Mock(return_value=json.dumps({"artifacts": []}))
    monkeypatch.setattr(downloader.subprocess, "check_output", call)
    assert downloader.pages("123", "artifacts", "artifacts") == []
    assert call.call_count == 1
