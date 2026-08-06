from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
import unittest

from protocols.oauth import OAuthTokens
from protocols.spotify.spotify_token_store import SpotifyTokenStore


class SpotifyTokenStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.token_path = (
            Path(self.temporary_directory.name)
            / "spotify"
            / "tokens.json"
        )
        self.store = SpotifyTokenStore(self.token_path)
        self.tokens = OAuthTokens(
            access_token="access-token",
            refresh_token="refresh-token",
            expires_at=1234.5,
            token_type="Bearer",
            scope="user-read-playback-state",
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_save_and_load_tokens(self) -> None:
        self.store.save(self.tokens)

        self.assertEqual(self.store.load(), self.tokens)

    def test_save_restricts_directory_and_file_permissions(self) -> None:
        previous_umask = os.umask(0)
        try:
            self.store.save(self.tokens)
        finally:
            os.umask(previous_umask)

        directory_mode = stat.S_IMODE(
            self.token_path.parent.stat().st_mode
        )
        file_mode = stat.S_IMODE(self.token_path.stat().st_mode)

        self.assertEqual(directory_mode, 0o700)
        self.assertEqual(file_mode, 0o600)

    def test_save_repairs_existing_permissions(self) -> None:
        self.token_path.parent.mkdir(mode=0o755)
        self.token_path.write_text("{}", encoding="utf-8")
        self.token_path.chmod(0o644)

        self.store.save(self.tokens)

        self.assertEqual(
            stat.S_IMODE(self.token_path.parent.stat().st_mode),
            0o700,
        )
        self.assertEqual(
            stat.S_IMODE(self.token_path.stat().st_mode),
            0o600,
        )

    def test_clear_removes_saved_tokens(self) -> None:
        self.store.save(self.tokens)

        self.store.clear()

        self.assertFalse(self.token_path.exists())


if __name__ == "__main__":
    unittest.main()
