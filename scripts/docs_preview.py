#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Serve repository Markdown through Grip with working relative links."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote

LINK_STYLE = """
<style id="openroadcode-docs-preview-links">
.markdown-body a {
    color: #0969da !important;
    text-decoration: underline !important;
    text-underline-offset: 0.15em;
}
.markdown-body a:visited {
    color: #8250df !important;
}
</style>
""".strip()


def document_route(source_root: Path, document: Path) -> str:
    """Return the URL route for a document inside the served repository."""
    root = source_root.resolve()
    resolved = document.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Document is outside repository: {resolved}") from exc
    return "/" + quote(relative.as_posix(), safe="/.-_")


def inject_preview_style(html: str) -> str:
    """Add link styling to a rendered Grip page without modifying Markdown."""
    if LINK_STYLE in html or "</head>" not in html:
        return html
    return html.replace("</head>", f"{LINK_STYLE}\n</head>", 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6419)
    args = parser.parse_args()

    source_root = args.source.resolve()
    document = args.document
    if not document.is_absolute():
        document = source_root / document
    document = document.resolve()

    if not document.is_file():
        raise SystemExit(f"Markdown file not found: {document}")

    try:
        route = document_route(source_root, document)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        from grip import create_app
    except ImportError as exc:
        raise SystemExit(
            "The 'grip' Markdown preview server is not installed.\n\n"
            "Install it in the active Python environment with:\n\n"
            "    python -m pip install grip"
        ) from exc

    app = create_app(path=str(source_root))

    @app.after_request
    def add_preview_link_style(response):  # type: ignore[no-untyped-def]
        if response.mimetype == "text/html":
            html = response.get_data(as_text=True)
            response.set_data(inject_preview_style(html))
            response.content_length = len(response.get_data())
        return response

    print(f"Previewing: {document}")
    print(f"Open:       http://{args.host}:{args.port}{route}")
    print("Press Ctrl-C to stop the preview server.")
    print()

    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
