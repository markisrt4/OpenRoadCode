# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT

from pathlib import Path

from scripts.setup_youtube_credentials import read_api_key, update_secrets


def test_updates_api_key_without_overwriting_other_secrets(tmp_path: Path) -> None:
    path=tmp_path/"secrets.env"
    path.write_text("SPOTIFY_CLIENT_ID=spotify\nYOUTUBE_API_KEY=old\nYOUTUBE_API_KEY=duplicate\n",encoding="utf-8")

    update_secrets(path,"new-key")

    text=path.read_text(encoding="utf-8")
    assert "SPOTIFY_CLIENT_ID=spotify" in text
    assert text.count("YOUTUBE_API_KEY=") == 1
    assert read_api_key(path) == "new-key"
    assert path.stat().st_mode & 0o777 == 0o600


def test_adds_api_key_to_new_secrets_file(tmp_path: Path) -> None:
    path=tmp_path/"openroadcode"/"secrets.env"

    update_secrets(path,"new-key")

    assert path.read_text(encoding="utf-8") == "YOUTUBE_API_KEY=new-key\n"
    assert path.parent.stat().st_mode & 0o777 == 0o700
