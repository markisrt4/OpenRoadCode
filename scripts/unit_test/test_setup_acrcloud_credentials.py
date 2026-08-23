# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path

from scripts.setup_acrcloud_credentials import read_assignments, update_secrets


def test_updates_credentials_without_overwriting_other_secrets(tmp_path: Path) -> None:
    path=tmp_path/"secrets.env"
    path.write_text("SPOTIFY_CLIENT_ID=spotify\nACRCLOUD_HOST=old\nACRCLOUD_HOST=duplicate\n",encoding="utf-8")
    update_secrets(path,{"ACRCLOUD_HOST":"new-host","ACRCLOUD_ACCESS_KEY":"key","ACRCLOUD_ACCESS_SECRET":"secret"})
    text=path.read_text(encoding="utf-8")
    assert "SPOTIFY_CLIENT_ID=spotify" in text
    assert text.count("ACRCLOUD_HOST=") == 1
    assert read_assignments(path) == {"ACRCLOUD_HOST":"new-host","ACRCLOUD_ACCESS_KEY":"key","ACRCLOUD_ACCESS_SECRET":"secret"}
    assert path.stat().st_mode & 0o777 == 0o600
