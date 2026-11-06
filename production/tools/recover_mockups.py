#!/usr/bin/env python3
"""Recover the bundled design-canvas mockups into inspectable pages.

The source is `forms_verse mockups.html`, a self-extracting artifact bundle:
a top-level `__bundler/manifest` holds gzip+base64 page documents, and each
page document is itself a small bundle with its referenced images/scripts.

Usage:
  python3 production/tools/recover_mockups.py \
      "/path/forms_verse mockups.html" production/reference/mockups

Output is private design evidence. It contains no cleared release asset; the
mockup photography is not an author-supplied scan.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import html
import json
import re
import sys
from pathlib import Path

MANIFEST_RE = r'<script type="__bundler/manifest">(.*?)</script>'
EXT = {
    "text/html": ".html",
    "image/webp": ".webp",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "text/javascript": ".js",
    "application/javascript": ".js",
    "text/css": ".css",
    "font/woff2": ".woff2",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_entry(entry: dict) -> bytes:
    raw = base64.b64decode(entry["data"])
    if entry.get("compressed"):
        raw = gzip.decompress(raw)
    return raw


def parse_manifest(text: str) -> dict:
    m = re.search(MANIFEST_RE, text, re.S)
    if not m:
        raise ValueError("no __bundler/manifest in document")
    return json.loads(m.group(1))


def page_order(text: str) -> list[str]:
    m = re.search(r'<script type="__bundler/page_order">(.*?)</script>', text, re.S)
    if not m:
        raise ValueError("no __bundler/page_order in document")
    return json.loads(m.group(1))


def template_boards(text: str) -> list[dict]:
    m = re.search(r'<script type="__bundler/template">(.*?)</script>', text, re.S)
    if not m:
        return []
    template = json.loads(m.group(1))
    boards = []
    for iframe in re.findall(r"<iframe[^>]+>", template):
        src = re.search(r'src="about:blank#([0-9a-f-]+)"', iframe)
        title = re.search(r'title="([^"]*)"', iframe)
        width = re.search(r'width="(\d+)"', iframe)
        height = re.search(r'height="(\d+)"', iframe)
        if src:
            boards.append({
                "id": src.group(1),
                "title": html.unescape(title.group(1)) if title else "",
                "width": int(width.group(1)) if width else None,
                "height": int(height.group(1)) if height else None,
            })
    return boards


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    source = Path(sys.argv[1])
    out = Path(sys.argv[2])
    text = source.read_text(encoding="utf-8")

    top = parse_manifest(text)
    order = page_order(text)
    boards = {b["id"]: b for b in template_boards(text)}

    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for uuid in order:
        short = uuid[:8]
        entry = top.get(uuid)
        if not entry or entry.get("mime") != "text/html":
            print(f"warning: page {uuid} missing", file=sys.stderr)
            continue
        page_bytes = decode_entry(entry)
        page_text = page_bytes.decode("utf-8")
        page_path = out / f"{short}.html"
        page_path.write_bytes(page_bytes)

        # The page's own resources: write them beside a per-page folder.
        res_dir = out / "resources" / short
        res_dir.mkdir(parents=True, exist_ok=True)
        resources = []
        try:
            page_manifest = parse_manifest(page_text)
        except ValueError:
            page_manifest = {}
        for rid, rentry in page_manifest.items():
            data = decode_entry(rentry)
            ext = EXT.get(rentry.get("mime", ""), ".bin")
            rp = res_dir / f"{rid[:8]}{ext}"
            rp.write_bytes(data)
            resources.append({
                "id": rid[:8],
                "mime": rentry.get("mime"),
                "path": str(rp.relative_to(out)),
                "bytes": len(data),
                "sha256": sha256_bytes(data),
            })

        board = boards.get(uuid, {})
        rows.append({
            "id": uuid,
            "short": short,
            "title": board.get("title") or re.search(r"<title>([^<]*)</title>", page_text).group(1),
            "frame": [board.get("width"), board.get("height")],
            "html": page_path.name,
            "html_sha256": sha256_bytes(page_bytes),
            "html_bytes": len(page_bytes),
            "resources": resources,
        })

    index = {
        "schema": "t07.recovered-mockups.v1",
        "source": source.name,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_bytes": source.stat().st_size,
        "note": (
            "Recovered private design evidence from a bundled artifact. The "
            "photography in the mockups is not an author scan and is not a "
            "releasable asset."
        ),
        "boards": rows,
    }
    (out / "recovered-index.json").write_text(
        json.dumps(index, indent=2) + "\n", encoding="utf-8"
    )

    md = [
        "# Recovered mockup boards",
        "",
        f"Source: `{source.name}` ({source.stat().st_size} bytes, "
        f"`{index['source_sha256'][:16]}…`)",
        "",
        "Private design evidence, recovered from the bundled artifact. The "
        "mockup photography is not the author's scan and is not cleared for use.",
        "",
        "| board | recovered page | frame | resources |",
        "|---|---|---|---|",
    ]
    for r in rows:
        md.append(
            f"| {r['title']} | `{r['html']}` | {r['frame'][0]}×{r['frame'][1]} | "
            f"{len(r['resources'])} |"
        )
    md += [
        "",
        "Each page is a self-extracting HTML document. `resources/<short>/` "
        "contains the referenced images/scripts decoded for inspection. Open "
        "the HTML file directly in a browser; it does not need a server.",
        "",
        "Recover with:",
        "",
        "```sh",
        'python3 production/tools/recover_mockups.py "<source>.html" production/reference/mockups',
        "```",
        "",
    ]
    (out / "INDEX.md").write_text("\n".join(md), encoding="utf-8")
    print(f"recovered {len(rows)} boards -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
