#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
"""Generate a temporary Jekyll site from OpenRoadCode documentation."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote

from docs_inventory import discover


LINK_PATTERN = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


def slugify_path(path: Path) -> str:
    parts = []
    for part in path.parts:
        value = part.lower().replace("_", "-")
        value = re.sub(r"[^a-z0-9.-]+", "-", value).strip("-")
        if value:
            parts.append(value)
    return "/".join(parts)


def preview_url(record: dict[str, str]) -> str:
    relative = Path(record["path"])
    kind = record["kind"]

    if relative == Path("docs/README.md"):
        return "/docs/"
    if relative == Path("README.md"):
        return "/docs/project/"
    if kind == "readme":
        return f"/docs/{slugify_path(relative.parent)}/"
    if kind == "contributing":
        return "/docs/contributing/"
    if kind == "curated":
        stem = relative.with_suffix("")
        return f"/docs/{slugify_path(stem)}/"

    relative_guide = relative.relative_to("docs").with_suffix("")
    return f"/docs/{slugify_path(relative_guide)}/"


def rewrite_links(
    markdown: str,
    source_path: Path,
    source_root: Path,
    routes: dict[Path, str],
) -> str:
    def replace(match: re.Match[str]) -> str:
        label, destination = match.groups()
        destination = destination.strip()
        if not destination or destination.startswith(
            ("http://", "https://", "mailto:", "tel:", "#", "/")
        ):
            return match.group(0)

        target, separator, fragment = destination.partition("#")
        target_path = (source_path.parent / target).resolve()

        route = routes.get(target_path)
        if route is None and target_path.is_dir():
            route = routes.get((target_path / "README.md").resolve())

        if route is None:
            try:
                relative = target_path.relative_to(source_root)
            except ValueError:
                return match.group(0)
            if target_path.exists():
                route = "/source/" + quote(relative.as_posix(), safe="/.-_")
            else:
                return match.group(0)

        if separator and fragment:
            route += f"#{fragment}"
        return f"[{label}]({route})"

    return LINK_PATTERN.sub(replace, markdown)


def write_layout(site_root: Path) -> None:
    layouts = site_root / "_layouts"
    assets = site_root / "assets"
    layouts.mkdir(parents=True, exist_ok=True)
    assets.mkdir(parents=True, exist_ok=True)

    (layouts / "default.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ page.title | default: "OpenRoadCode Documentation" }}</title>
  <link rel="stylesheet" href="/assets/docs-preview.css">
</head>
<body>
  <main class="docs">
    {{ content }}
  </main>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";

    const blocks = document.querySelectorAll("pre > code.language-mermaid");
    for (const block of blocks) {
      const diagram = document.createElement("div");
      diagram.className = "mermaid";
      diagram.textContent = block.textContent;
      block.parentElement.replaceWith(diagram);
    }

    mermaid.initialize({
      startOnLoad: false,
      securityLevel: "strict",
      theme: "neutral",
      themeVariables: {
        fontSize: "17px",
        fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
      },
      flowchart: {
        htmlLabels: true,
        nodeSpacing: 38,
        rankSpacing: 48
      }
    });
    await mermaid.run({ nodes: document.querySelectorAll(".mermaid") });
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )

    (assets / "docs-preview.css").write_text(
        """:root {
  --orc-green: #84ce1f;
  --orc-blue: #168bd1;
  --orc-orange: #f15a16;
  --orc-text: #1f2328;
  --orc-muted: #59636e;
  --orc-line: #d0d7de;
}
html { font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
body { margin: 0; background: #f3f5f7; color: var(--orc-text); }
.docs {
  max-width: 1040px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 34px 42px 64px;
  box-sizing: border-box;
  background: #fff;
  border-inline: 1px solid #e1e5e9;
}
h1, h2, h3 { line-height: 1.15; }
h1 { border-bottom: 2px solid var(--orc-blue); padding-bottom: .45rem; }
h2 { margin-top: 2.5rem; }
a { color: #0969da; text-decoration: underline; text-underline-offset: .16em; }
a:visited { color: #8250df; }
code { background: #eff1f3; padding: .15em .35em; border-radius: 4px; }
pre { overflow-x: auto; background: #f6f8fa; padding: 16px; border: 1px solid var(--orc-line); border-radius: 10px; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; max-width: 100%; display: block; overflow-x: auto; }
th, td { border: 1px solid var(--orc-line); padding: 7px 10px; }
th { background: #f6f8fa; }
blockquote { border-left: 4px solid var(--orc-orange); margin-left: 0; padding-left: 16px; color: var(--orc-muted); }
.mermaid { margin: 1.35rem 0 2rem; padding: 1rem; border-radius: 14px; background: #f7f9fb; overflow-x: auto; }
.mermaid svg { min-width: 760px; max-width: none !important; height: auto; }
.mermaid .nodeLabel, .mermaid .edgeLabel { font-size: 17px !important; line-height: 1.3; }
.orc-diagram-legend {
  float: right;
  width: 180px;
  margin: 0 0 1rem 1.4rem;
  padding: .65rem .75rem;
  border: 1px solid var(--orc-line);
  border-radius: 10px;
  background: #f8fafc;
  box-shadow: 0 6px 18px rgba(31,35,40,.08);
  font-size: .72rem;
  line-height: 1.35;
}
.orc-diagram-legend strong {
  display: block;
  margin-bottom: .45rem;
  color: #39424e;
  font-size: .68rem;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.orc-diagram-legend span {
  display: flex;
  align-items: center;
  gap: .42rem;
  margin: .22rem 0;
  color: var(--orc-muted);
}
.orc-legend-swatch {
  width: .68rem;
  height: .68rem;
  flex: 0 0 .68rem;
  border: 1px solid;
  border-radius: 3px;
}
.orc-legend-app { background: #dbeafe; border-color: #2563eb; }
.orc-legend-service { background: #ede9fe; border-color: #7c3aed; }
.orc-legend-controller { background: #dcfce7; border-color: #16a34a; }
.orc-legend-message { background: #ffedd5; border-color: #ea580c; }
.orc-legend-adapter { background: #fee2e2; border-color: #dc2626; }
.orc-legend-external { background: #f3f4f6; border-color: #6b7280; }
@media (max-width: 700px) {
  .docs { padding: 22px 18px 48px; border-inline: 0; }
  .orc-diagram-legend { float: none; width: auto; max-width: 240px; margin: .75rem 0 1.25rem auto; }
  .mermaid { padding: .75rem; }
  .mermaid svg { min-width: 680px; }
}
""",
        encoding="utf-8",
    )


def build_site(source_root: Path, site_root: Path) -> int:
    source_root = source_root.resolve()
    site_root = site_root.resolve()

    if site_root.exists():
        shutil.rmtree(site_root)
    site_root.mkdir(parents=True)

    records = discover(source_root)
    routes: dict[Path, str] = {}
    for record in records:
        routes[(source_root / record["path"]).resolve()] = preview_url(record)

    write_layout(site_root)
    (site_root / "_config.yml").write_text(
        'title: "OpenRoadCode Documentation"\n'
        'markdown: kramdown\n'
        'permalink: pretty\n'
        'exclude: []\n',
        encoding="utf-8",
    )

    for record in records:
        source_path = (source_root / record["path"]).resolve()
        markdown = source_path.read_text(encoding="utf-8")
        markdown = rewrite_links(markdown, source_path, source_root, routes)
        url = routes[source_path]
        title = record["title"]

        output_dir = site_root / url.strip("/")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "index.md").write_text(
            "---\n"
            "layout: default\n"
            f"title: {json.dumps(title)}\n"
            f"permalink: {url!r}\n"
            "---\n\n"
            + markdown
            + "\n",
            encoding="utf-8",
        )

    source_output = site_root / "source"
    source_output.mkdir(parents=True, exist_ok=True)
    for relative in (Path("Doxyfile"), Path("SECURITY.md"), Path("docs/vehicle-one-wire.pdf")):
        path = source_root / relative
        if path.is_file():
            target = source_output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)

    print(f"Generated Jekyll preview for {len(records)} documents: {site_root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return build_site(args.source, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
