# SPDX-License-Identifier: MIT
"""Spotify application-setting persistence checks."""

from unittest.mock import Mock

from apps.orcUi.adapters.spotify_application_settings import (
    SpotifyApplicationSettingsStore,
    create_spotify_secret_manager,
)

USER_CLIENT = "a" * 32
SYSTEM_CLIENT = "b" * 32
ENVIRONMENT_CLIENT = "c" * 32


def test_client_id_round_trips_in_private_xdg_record(tmp_path):
    path = tmp_path / "openroadcode" / "spotify" / "application.json"
    store = SpotifyApplicationSettingsStore(path)

    store.save_client_id(f" {USER_CLIENT} ")

    assert store.load_client_id() == USER_CLIENT
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700


def test_missing_or_invalid_record_is_unconfigured(tmp_path):
    path = tmp_path / "application.json"
    store = SpotifyApplicationSettingsStore(path)
    assert store.load_client_id() is None
    path.write_text("not json", encoding="utf-8")
    assert store.load_client_id() is None
    path.write_text('{"client_id": "access-token-not-client-id"}', encoding="utf-8")
    assert store.load_client_id() is None


def test_client_id_rejects_non_client_tokens(tmp_path):
    store = SpotifyApplicationSettingsStore(tmp_path / "application.json")
    try:
        store.save_client_id("not-an-api-client-id")
    except ValueError as error:
        assert "32-character" in str(error)
    else:
        raise AssertionError("whitespace must be rejected")


def test_resolution_prefers_environment_then_user_then_system(tmp_path):
    store = SpotifyApplicationSettingsStore(tmp_path / "application.json")
    store.save_client_id(USER_CLIENT)

    assert store.resolve_client_id(
        environment_value=ENVIRONMENT_CLIENT, system_value=SYSTEM_CLIENT,
    ) == ENVIRONMENT_CLIENT
    assert store.resolve_client_id(
        environment_value=None, system_value=SYSTEM_CLIENT,
    ) == USER_CLIENT

    empty = SpotifyApplicationSettingsStore(tmp_path / "missing.json")
    assert empty.resolve_client_id(
        environment_value=None, system_value=SYSTEM_CLIENT,
    ) == SYSTEM_CLIENT


def test_resolved_secret_manager_preserves_system_redirect(tmp_path):
    store = SpotifyApplicationSettingsStore(tmp_path / "application.json")
    store.save_client_id(USER_CLIENT)
    system = Mock()
    system.get_secret.side_effect = lambda name: {
        "SPOTIFY_CLIENT_ID": SYSTEM_CLIENT,
        "SPOTIFY_REDIRECT_URI": "http://127.0.0.1:9999/callback",
    }.get(name)

    secrets = create_spotify_secret_manager(
        store, system_secrets=system, environment={},
    )

    assert secrets.get_secret("SPOTIFY_CLIENT_ID") == USER_CLIENT
    assert secrets.get_secret("SPOTIFY_REDIRECT_URI") == "http://127.0.0.1:9999/callback"
