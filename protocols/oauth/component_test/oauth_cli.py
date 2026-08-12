#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT


from __future__ import annotations

import argparse
import secrets

from protocols.oauth import (
    OAuthClient,
    OAuthClientConfig,
    create_pkce_pair,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OAuth protocol component test"
    )

    parser.add_argument(
        "--client-id",
        default="example-client-id",
        help="OAuth client identifier",
    )

    parser.add_argument(
        "--authorization-url",
        default="https://example.com/oauth/authorize",
        help="OAuth authorization endpoint",
    )

    parser.add_argument(
        "--token-url",
        default="https://example.com/oauth/token",
        help="OAuth token endpoint",
    )

    parser.add_argument(
        "--redirect-uri",
        default="http://127.0.0.1:8888/callback",
        help="OAuth redirect URI",
    )

    parser.add_argument(
        "--scope",
        action="append",
        default=[],
        help="OAuth scope; may be specified multiple times",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    config = OAuthClientConfig(
        client_id=args.client_id,
        authorization_url=args.authorization_url,
        token_url=args.token_url,
        redirect_uri=args.redirect_uri,
        scopes=tuple(args.scope),
    )

    client = OAuthClient(config)

    pkce = create_pkce_pair()
    state = secrets.token_urlsafe(24)

    authorization_url = client.build_authorization_url(
        state=state,
        code_challenge=pkce.challenge,
    )

    print("OAuth component test")
    print()
    print(f"State: {state}")
    print(f"PKCE verifier: {pkce.verifier}")
    print(f"PKCE challenge: {pkce.challenge}")
    print(f"Challenge method: {pkce.challenge_method}")
    print()
    print("Authorization URL:")
    print(authorization_url)


if __name__ == "__main__":
    main()
