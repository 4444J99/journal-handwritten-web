#!/usr/bin/env python3
"""Build the private playground into playground/dist/.

The playground is a read-only companion to the three deployments (Studio, Staging,
Live). It gathers everything this repository holds about the project, plus the
claude.ai artifacts listed in playground/sources.json, into one static page.

    python3 playground/build.py            # writes playground/dist/
    python3 playground/build.py --out DIR  # writes elsewhere

PRIVATE. The output contains every page, draft, Reserve candidate and record.
Serve it only behind the studio's Cloudflare Access login or as a private
claude.ai artifact. Never copy it to versforms, Staging or Live.

Reads: studio/data/review.json, site/data/j.json, studio/img/thumbs, site/img/i,
site/img/s, claude/, docs/, production/exports/, release/packets/,
playground/designs/, playground/snapshots/, playground/sources.json.
Writes only into the output directory.
"""
import argparse
import os
import csv
import json
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
PG = ROOT / "playground"
MD = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])


SKELETON = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head><body>
%PAGE%
</body></html>
"""


def md_html(text):
    MD.reset()
    return MD.convert(text)


def title_of(text, fallback):
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def table_cell(text, label):
    m = re.search(r"^\|\s*" + re.escape(label) + r"\s*\|\s*(.+?)\s*\|\s*$", text, re.M)
    return m.group(1) if m else ""


def research_map():
    """Report file name -> chat record slug, from claude/README.md."""
    out = {}
    for line in (ROOT / "claude/README.md").read_text().splitlines():
        m = re.match(r"\|\s*`([^`]+)`\s*\|\s*`?([0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]+)`?", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def build_docs(out):
    docs = []
    rmap = research_map()
    # research reports
    for p in sorted((ROOT / "claude").glob("*.md")):
        if p.name in ("README.md", "plan.md"):
            continue
        t = p.read_text()
        chat = rmap.get(p.name, "")
        docs.append({"id": "r-" + re.sub(r"[^a-z0-9]+", "-", p.stem.lower())[:60].strip("-"), "kind": "research",
                     "title": title_of(t, p.stem.replace("_", ":")), "date": chat[:10], "chat": chat,
                     "path": str(p.relative_to(ROOT)), "words": len(t.split()), "html": md_html(t)})
    # pdfs
    pdfs = []
    for p in sorted((ROOT / "claude").glob("*.pdf")):
        name = re.sub(r"[^A-Za-z0-9.]+", "-", p.name)
        copy(p, out / "pdf" / name)
        pdfs.append({"title": p.stem, "file": "pdf/" + name, "bytes": p.stat().st_size, "path": str(p.relative_to(ROOT))})
    # documents exported from claude.ai (playground/snapshots/docs)
    for p in sorted((PG / "snapshots/docs").glob("*.md")):
        t = p.read_text()
        m = re.search(r"^([A-Z][a-z]{2} \d{1,2}, 20\d\d)", t[t.find("\n"):].strip())
        date = __import__("datetime").datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat() if m else ""
        docs.append({"id": "a-" + p.stem[:60], "kind": "document", "title": title_of(t, p.stem), "date": date,
                     "path": str(p.relative_to(ROOT)), "words": len(t.split()), "html": md_html(t)})
    # plan
    t = (ROOT / "docs/plan.md").read_text()
    docs.append({"id": "plan", "kind": "plan", "title": "Project plan", "date": "", "path": "docs/plan.md",
                 "words": len(t.split()), "html": md_html(t)})
    # chat records and their exchanges
    chats = []
    for p in sorted((ROOT / "docs/chats").glob("*.md")):
        if p.name == "README.md":
            continue
        t = p.read_text()
        slug = p.stem
        ex = []
        d = p.with_suffix("")
        if d.is_dir():
            for e in sorted(d.glob("*.md")):
                et = e.read_text()
                ex.append({"id": "x-" + slug + "-" + e.stem[:2], "title": title_of(et, e.stem),
                           "date": (re.search(r"(\d{4}-\d{2}-\d{2})", table_cell(et, "Exchange")) or [None, slug[:10]])[1],
                           "issue": table_cell(et, "Issue"), "path": str(e.relative_to(ROOT)), "html": md_html(et)})
        status = table_cell(t, "Status")
        chat_url = table_cell(t, "Chat")
        m = re.search(r"\((https://claude\.ai/chat/[^)]+)\)", chat_url) or re.search(r"(https://claude\.ai/chat/\S+)", chat_url)
        chats.append({"id": "c-" + slug, "kind": "chat", "title": title_of(t, slug), "date": slug[:10], "status": status,
                      "url": m.group(1) if m else "", "path": str(p.relative_to(ROOT)), "html": md_html(t), "exchanges": ex})
    # other records: docs/** outside chats, plus component READMEs
    records = []
    paths = [p for p in sorted((ROOT / "docs").rglob("*.md")) if "chats" not in p.parts and p.name != "plan.md"]
    paths += [ROOT / x for x in ("README.md", "CHANGELOG.md", "studio-cf/README.md", "production/README.md",
                                  "production/DISPOSITION.md", "proto/alive/README.md", "proto/alive/DATA.md",
                                  "claude/README.md", "exports/studio-db-2026-11-05/README.md") if (ROOT / x).exists()]
    for p in paths:
        t = p.read_text()
        rel = p.relative_to(ROOT)
        group = rel.parts[1] if rel.parts[0] == "docs" and len(rel.parts) > 2 else ("docs" if rel.parts[0] == "docs" else rel.parts[0] if len(rel.parts) > 1 else "repository")
        m = re.search(r"(20\d{2}-\d{2}-\d{2})", str(rel)) or re.search(r"(20\d{2}-\d{2}-\d{2})", t[:600])
        records.append({"id": "d-" + re.sub(r"[^a-z0-9]+", "-", str(rel).lower()).strip("-")[:80], "kind": "record",
                        "group": group, "title": title_of(t, p.stem), "date": m.group(1) if m else "",
                        "path": str(rel), "words": len(t.split()), "html": md_html(t)})
    return docs, pdfs, chats, records


def build_catalog(out):
    r = json.loads((ROOT / "studio/data/review.json").read_text())
    j = json.loads((ROOT / "site/data/j.json").read_text())
    accepted = j.get("acceptedReadings", {})
    corrected = {k: v for k, v in r.get("acceptedReviews", {}).items() if v.get("status") == "corrected" and isinstance(v.get("text"), str)}

    def reading(line):
        # Same precedence as the reader's prepData: an accepted reading replaces the machine reading.
        if line["id"] in accepted:
            return accepted[line["id"]]
        if line["id"] in corrected:
            return corrected[line["id"]]["text"]
        return line["tx"]

    pages = []
    for p in r["pages"]:
        pid = p["id"]
        copy(ROOT / "studio" / p["thumb"], out / "img/t" / (pid + ".jpg"))
        # Mid-size scans and 2015 spreads are served once, from the reader copy (reader/img/...).
        if not (ROOT / "site/img/i" / (pid + ".jpg")).exists():
            raise SystemExit(f"missing site/img/i/{pid}.jpg")
        sp = None
        if p.get("spread"):
            name = Path(p["spread"]["img"]).name
            if (ROOT / "site/img/s" / name).exists():
                sp = "reader/img/s/" + name
        pages.append({"id": pid, "seq": p["seq"], "w": p["w"], "h": p["h"], "spread": sp, "uncertain": p["uncertain"],
                      "blocks": [{"t": b["t"], "note": b.get("note", ""), "spread": b.get("spread", False),
                                  "lines": [{"id": l["id"], "tx": reading(l), **({"machine": l["tx"]} if reading(l) != l["tx"] else {})} for l in b["lines"]]} for b in p["blocks"]]})
    jv = {pc["id"]: [{"id": v["id"], "s": v.get("s"), "d": v.get("d"), "P": v["P"]} for v in pc["V"]] for pc in j["pieces"]}
    items = []
    for it in r["items"]:
        items.append({**it, "stack": jv.get(it["id"], [])})
    return {"pages": pages, "items": items, "flagged": r["flagged"], "groups": j["groups"],
            "accepted": sorted(r.get("acceptedReviews", {}).keys()), "acceptedReadings": j.get("acceptedReadings", {}),
            "prov": j.get("prov", {})}


def build_media(out):
    media = []
    base = ROOT / "production/exports"
    for piece in sorted(d for d in base.iterdir() if d.is_dir()):
        files = []
        for f in sorted(piece.rglob("*")):
            if f.suffix.lower() not in (".jpg", ".png", ".mp4") or not f.is_file():
                continue
            rel = f.relative_to(base)
            copy(f, out / "media" / rel)
            files.append({"file": "media/" + str(rel), "group": rel.parts[1], "name": str(Path(*rel.parts[2:])),
                          "bytes": f.stat().st_size, "video": f.suffix == ".mp4"})
        man = piece / "MANIFEST.md"
        media.append({"piece": piece.name, "files": files, "manifest": md_html(man.read_text()) if man.exists() else ""})
    return media


def build_release():
    pk = ROOT / "release/packets/2026-11-05-t03-current"
    def rows(name):
        with open(pk / name, newline="") as fh:
            return list(csv.DictReader(fh))
    return {"packet": str(pk.relative_to(ROOT)), "queue": rows("first-release-queue.csv"),
            "slots": rows("release-tracker-100-slots.csv"),
            "public": json.loads((ROOT / "release/public.json").read_text()),
            "dryrun": (pk / "gated-dry-run.txt").read_text()}


def build_designs(out):
    boards = json.loads((PG / "designs/boards.json").read_text())
    for slug in boards:
        for b in boards[slug]["boards"]:
            copy(PG / "designs" / slug / b["file"], out / "designs" / slug / b["file"])
    for d in sorted((PG / "snapshots").iterdir()):
        if not d.is_dir() or d.name in SNAPSHOT_DATA_ONLY:
            continue
        rules = SNAPSHOT_REWRITES.get(d.name, [])
        used = set()
        for f in d.rglob("*"):
            if not f.is_file():
                continue
            dst = out / "snap" / d.name / f.relative_to(d)
            copy(f, dst)
            if f.suffix in (".html", ".json"):
                text = f.read_text()
                for old_path, new_path in rules:
                    if old_path in text:
                        used.add(old_path)
                        text = text.replace(old_path, new_path)
                if f.suffix == ".html" and not text[:200].lower().lstrip().startswith("<!doctype"):
                    # artifact pages are stored without a skeleton; served as a plain file they need one
                    text = SKELETON.replace("%PAGE%", text)
                dst.write_text(text)
        missing = [r[0] for r in rules if r[0] not in used]
        if missing:
            raise SystemExit(f"snapshot {d.name}: expected paths not found: {missing}")
    return boards


# Snapshot pages that were published with their own copies of the scans load the
# playground's shared copies instead (same bytes; checked when the snapshots were taken).
SNAPSHOT_REWRITES = {
    "first-reader": [("img/plates/", "../../reader/img/h/"), ("img/${esc(id)}.jpg", "../../reader/img/p/${esc(id)}.jpg"),
                     ('"img/thumbs/', '"../../img/t/'), ('"img/spreads/', '"../../reader/img/s/'), ('"img/diary', '"../../reader/img/p/diary')],
    "canvas-test": [('{dir:"img/thumbs/"', '{dir:"../../img/t/"'), ('{dir:"img/", h:1600}', '{dir:"../../reader/img/p/", h:1600}')],
}
# Snapshots whose content the playground renders itself (from data), not as a page.
SNAPSHOT_DATA_ONLY = {"docs", "versforms-progress"}


def build_reader(out):
    """The merged piece (site/), as the reader prototype and the shared scan store."""
    for f in sorted((ROOT / "site").rglob("*")):
        if f.is_file() and f.name != "_worker.js":
            copy(f, out / "reader" / f.relative_to(ROOT / "site"))


def build_progress():
    base = PG / "snapshots/versforms-progress/data"
    return {f.stem: json.loads(f.read_text()) for f in sorted(base.glob("*.json"))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PG / "dist"))
    a = ap.parse_args(argv)
    # Compare lexically normalised paths, never resolved ones: a symlinked output
    # directory must not make its target count as the generated default.
    out = Path(os.path.abspath(a.out))
    default = Path(os.path.abspath(PG / "dist"))
    if out.is_symlink():
        raise SystemExit(f"refusing to write through a symlink: {out}")
    if out.exists() and out != default and any(out.iterdir()):
        raise SystemExit(f"refusing to write into a non-empty directory other than {default}: {out}")
    if out == default and out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    sources = json.loads((PG / "sources.json").read_text())
    docs, pdfs, chats, records = build_docs(out)
    data = {"built": __import__("datetime").date.today().isoformat(), "sources": sources,
            "catalog": build_catalog(out), "designs": build_designs(out), "media": build_media(out),
            "release": build_release(), "pdfs": pdfs, "progress": build_progress()}
    build_reader(out)
    (out / "data").mkdir()
    (out / "data/core.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (out / "data/docs.json").write_text(json.dumps({"docs": docs, "chats": chats, "records": records},
                                                  ensure_ascii=False, separators=(",", ":")))
    page = (PG / "index.html").read_text()
    # The claude.ai artifact host adds the document skeleton itself; a plain static host
    # (the studio's Pages project) needs it in the file.
    (out / "artifact.html").write_text(page)
    (out / "index.html").write_text(SKELETON.replace("%PAGE%", page))
    n = sum(1 for f in out.rglob("*") if f.is_file())
    size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"playground: {n} files, {size/1e6:.1f} MB -> {out}")
    print(f"  {len(data['catalog']['pages'])} pages, {len(data['catalog']['items'])} pieces, "
          f"{sum(len(b['boards']) for b in data['designs'].values())} design boards, {len(docs)} reports/plan, "
          f"{len(chats)} chats ({sum(len(c['exchanges']) for c in chats)} exchanges), {len(records)} records, "
          f"{sum(len(m['files']) for m in data['media'])} media files, {len(pdfs)} PDFs")


if __name__ == "__main__":
    main()
