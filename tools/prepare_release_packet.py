#!/usr/bin/env python3
"""Prepare a private, inspectable release packet without changing release state.

Uses PR #101's source, review, selection, font, builder and output-check functions.
This is a preparation/audit command, never a posting command. Exit 0 means that a
packet was produced, not that a release is cleared. See packet.json's gates.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import build_public
import post_poem as posting

ROOT = Path(__file__).resolve().parent.parent
SOURCE_RECORD = "docs/chats/2026-11-05-local-session-finish-and-launch.md"
ECHO = [("echo-diary37", "diary37", [2]),
        ("echo-diary53a", "diary53a", [4]),
        ("echo-diary60a", "diary60a", [3]),
        ("echo-diary59", "diary59", [4])]
PAIR_DEFS = [("same-song-diary61a-diary62", ["diary61a", "diary62"]),
             ("one-piece-diary56a-diary57", ["diary56a", "diary57"])]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def inventory(root):
    return [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size,
             "sha256": digest(p)} for p in sorted(root.rglob("*")) if p.is_file()]


def source_inputs(src, db_root):
    paths = set()
    for folder in [src.site, src.root / "studio", db_root]:
        paths.update(p.resolve() for p in folder.rglob("*") if p.is_file())
    paths.add(src.release_path.resolve())
    return {str(p): digest(p) for p in sorted(paths)}


def decision_state(doc):
    if not doc or not doc.get("choice"):
        return "awaiting-author"
    if "derived" in str(doc.get("note", "")).lower():
        return "derived-default-awaiting-confirmation"
    # A database value has provenance to inspect; it is not independent proof
    # of the actor's identity or current release authorization.
    return "recorded-choice-needs-provenance-check"


def review_ok(doc):
    return bool(doc and (doc.get("status") == "confirmed" or
                        doc.get("status") == "corrected" and isinstance(doc.get("text"), str)))


def catalog(src, db):
    order = {p["id"]: n for n, p in enumerate(src.review["pages"])}
    rows = []
    for pid, pc in src.pieces.items():
        item = src.items[pid]
        pages = sorted({pg for v in pc["V"] for pg, _ in v["P"]}, key=order.get)
        idx, how, notes = posting.select_versions(src, db, pid, False)
        line_ids = list(dict.fromkeys(src.item_line_ids(pid) or []))
        pending = [lid for lid in line_ids if not review_ok(db["reviews"].get(lid))]
        rows.append({"piece_id": pid, "first_page": pages[0],
                     "page_sequence": src.rpages[pages[0]]["seq"], "pages": pages,
                     "recorded_kind": item["kind"], "recorded_status": item["status"],
                     "classification_provenance": "preserved catalog; not author release approval",
                     "pool": db["release"].get(pid, {}).get("pool"),
                     "version_count": len(pc["V"]),
                     "preview_version_ids": [pc["V"][i]["id"] for i in idx],
                     "preview_selection_basis": how, "selection_notes": notes,
                     "reviewed_lines": len(line_ids) - len(pending),
                     "total_lines": len(line_ids), "pending_line_ids": pending,
                     "batch_gate": dict(zip(("pass", "detail"), posting.gate_filed(db, pid)))})
    # Stable source order breaks ties; IDs are never replaced by ordinal numbers.
    return sorted(rows, key=lambda r: order[r["first_page"]])


def author_queue(src, db):
    rows = []
    seq = {p["id"]: p["seq"] for p in src.review["pages"]}

    def add(key, kind, pages, source, **extra):
        rows.append({"id": key, "category": kind, "pages": pages,
                     "page_sequence": min(seq[p] for p in pages) if pages else None,
                     "status": "awaiting-author", "source": source, **extra})

    for page in src.review["pages"]:
        pid = page["id"]
        line_ids = [line["id"] for b in page["blocks"] for line in b["lines"]]
        pending = [lid for lid in line_ids if not review_ok(db["reviews"].get(lid))]
        if pending:
            add("review-" + pid, "unreviewed-lines", [pid], "studio/data/review.json",
                pending_line_ids=pending, count=len(pending))
        for n, note in enumerate(page.get("uncertain", [])):
            add(f"uncertain-{pid}-{n:03d}", "uncertain-reading", [pid],
                f"studio/data/review.json#/pages/{src.review['pages'].index(page)}/uncertain/{n}",
                recorded_note=note, page_line_reviews_complete=not pending,
                status="retained-note-page-lines-reviewed" if not pending else "awaiting-author",
                resolution_note="Original uncertainty is retained; line reviews do not erase the note.")
        for bi, block in enumerate(page["blocks"]):
            if block["t"] == "quotation":
                add(f"quotation-{pid}-{bi}", "borrowed-passage", [pid],
                    "studio/data/review.json", blocks=[bi],
                    recorded_readings=[l["tx"] for l in block["lines"]],
                    action="Inspect scan exposure and source attribution; no authorship ruling made.")

    for pid, pc in src.pieces.items():
        if len(pc["V"]) < 2:
            continue
        pages = list(dict.fromkeys(pg for v in pc["V"] for pg, _ in v["P"]))
        key = next((k for k, p in posting.final_decision_pieces(src).items() if p == pid), "final-" + pid)
        doc = db["decisions"].get(key)
        idx, how, notes = posting.select_versions(src, db, pid, False)
        add(key, "final-version", pages, "site/data/j.json; studio/index.html decisionDefs()",
            piece_id=pid, versions=[{"index": i, **v} for i, v in enumerate(pc["V"])],
            preview_indices=idx, preview_basis=how, recorded_decision=doc,
            status=decision_state(doc), notes=notes)
    for key, pages in PAIR_DEFS:
        doc = db["decisions"].get(key)
        add(key, "possible-pair", pages, "studio/index.html renderDecisions(); docs/plan.md",
            recorded_decision=doc, status=decision_state(doc))
    echoes = ECHO + [(f"echo-diary46-{bi}", "diary46", [bi])
                     for bi, b in enumerate(src.rpages["diary46"]["blocks"])
                     if b["t"] == "text" and b["lines"]]
    for key, page, blocks in echoes:
        doc = db["decisions"].get(key)
        add(key, "possible-echo", [page], "studio/index.html ECHO / decisionDefs()",
            blocks=blocks, recorded_decision=doc, status=decision_state(doc))
    for f in src.review["flagged"]:
        doc = db["decisions"].get(f["key"])
        add(f["key"], "flagged-visibility", [f["page"]], "studio/data/review.json#/flagged",
            spread=f["spread"], recorded_decision=doc, status=decision_state(doc),
            action="Author decides public/private/later; a flag is not a classification.")
    for row in catalog(src, db):
        add("pool-" + row["piece_id"], "release-classification", row["pages"],
            "studio/data/review.json; exported release collection", piece_id=row["piece_id"],
            recorded_pool=row["pool"],
            status="recorded-pool-needs-clearance" if row["pool"] else "awaiting-author")
    return sorted(rows, key=lambda r: (r["page_sequence"] or 10**9, r["category"], r["id"]))


def exposure_map(src, selection):
    """Enumerate catalogued writing in every whole page or spread to be copied.

    Unlike shared_scan's posting allowance, this reports unselected versions of
    the SAME piece too. It does not treat --accept-shared-scan as authorization.
    """
    allowed = {(pg, bi) for pid, idx in selection.items()
               for pg, bi in src.published_blocks(pid, idx)}
    direct = {pg for pg, _ in allowed}
    mates = set(src.spread_mates(direct))
    pages = []
    for pg in src.j["pages"]:
        page_id = pg["id"]
        if page_id not in direct | mates:
            continue
        blocks = []
        for bi, block in enumerate(pg["B"]):
            occupants = [{"piece_id": pid, "version_id": v["id"], "version_index": vi,
                          "selected_version": vi in selection.get(pid, [])}
                         for pid, pc in src.pieces.items() for vi, v in enumerate(pc["V"])
                         if any(p == page_id and bi in bs for p, bs in v["P"])]
            rblock = src.rpages[page_id]["blocks"][bi]
            other = [it["id"] for it in src.review["items"] if it["id"] not in src.pieces
                     and any(v["page"] == page_id and bi in v["blocks"] for v in it["versions"])]
            has_writing = bool(any(block["L"]) or rblock["lines"])
            blocks.append({"block": bi, "type": rblock["t"], "occupants": occupants,
                           "other_item_ids": other, "selected_text": (page_id, bi) in allowed,
                           "writing_visible_in_image": has_writing,
                           "withheld_writing_visible": has_writing and (page_id, bi) not in allowed})
        files = [f"img/{s}/{page_id}.jpg" for s in ("p", "i", "m")] if page_id in direct else []
        if page_id in direct:
            files += ["img/a/t0.jpg", "img/a/k0.jpg"]
            if (src.site / "img" / "h" / (page_id + ".jpg")).exists():
                files.append(f"img/h/{page_id}.jpg")
        files += sorted({f"img/s/{src.jpages[p]['sp']['f']}.jpg" for p in direct
                         if (src.jpages[p].get("sp") or {}).get("f") and
                         (p == page_id or page_id in src.spread_mates([p]))})
        pages.append({"page_id": page_id, "page_sequence": src.rpages[page_id]["seq"],
                      "via": "selected page" if page_id in direct else "facing spread page",
                      "source_atlas_region": pg["a"], "files": files, "blocks": blocks})
    return {"selection": {p: [src.pieces[p]["V"][i]["id"] for i in idx] for p, idx in selection.items()},
            "pages": pages, "withheld_blocks_visible": [
                {"page_id": p["page_id"], **b} for p in pages for b in p["blocks"] if b["withheld_writing_visible"]],
            "limit": "Catalog and derivative audit; inspect the actual scans for uncatalogued marks and metadata."}


def expected_files(src, result):
    names = {"index.html", "_headers", "data/j.json", "img/a/t0.jpg", "img/a/k0.jpg"}
    for pid in result["pages"]:
        names.update(f"img/{s}/{pid}.jpg" for s in ("p", "i", "m"))
        page = src.jpages[pid]
        if (page.get("sp") or {}).get("f"):
            names.add(f"img/s/{page['sp']['f']}.jpg")
        if (src.site / "img/h" / f"{pid}.jpg").is_file():
            names.add(f"img/h/{pid}.jpg")
    return names


def audit_preview(src, db, pid, indices, out):
    corrections, counts, stale = posting.load_corrections(src, db, pid, indices)
    if stale:
        raise ValueError("Stale review originals; no preview built: " + ", ".join(stale))
    result = build_public.build(out, [pid], site=src.site, select={pid: indices}, corrections=corrections)
    if result.get("font_error"):
        raise ValueError("Font tooling unavailable: " + result["font_error"])
    published = set(map(tuple, result["published"]))
    texts = {corrections.get((pg, bi, li), text)
             for pg, bi in published for li, text in enumerate(src.jpages[pg]["B"][bi]["L"])}
    checks = [{"check": name, "pass": ok, "detail": detail}
              for name, ok, detail in posting.check_output(src, out, [pid], published, texts, [pid])]
    files = inventory(out)
    actual = {f["path"] for f in files}
    expected = expected_files(src, result)
    checks.append({"check": "exact file whitelist, including images, spreads and plates",
                   "pass": actual == expected, "detail": {"extra": sorted(actual - expected), "missing": sorted(expected - actual)}})
    exposure = exposure_map(src, {pid: indices})
    checks.append({"check": "no catalogued withheld block visible in any included image",
                   "pass": not exposure["withheld_blocks_visible"],
                   "detail": [{"page": b["page_id"], "block": b["block"]} for b in exposure["withheld_blocks_visible"]]})
    pub = json.loads((out / "data/j.json").read_text())
    images = []
    from PIL import Image
    for f in files:
        p = out / f["path"]
        if p.suffix != ".jpg":
            continue
        with Image.open(p) as im:
            row = {**f, "width": im.width, "height": im.height,
                   "metadata_keys": sorted(im.info), "exif_tags": {str(k): str(v) for k, v in im.getexif().items()}}
        if not f["path"].startswith("img/a/"):
            source = src.site / f["path"]
            row["source"] = "site/" + f["path"]
            row["source_sha256"] = digest(source)
            row["byte_identical_to_source"] = row["source_sha256"] == f["sha256"]
        images.append(row)
    # Reconstruct each atlas exclusively from the declared input page regions.
    # This compares exact encoded bytes, including padding, not a permissive
    # similarity threshold that could overlook a neighbouring page.
    atlas_checks = []
    for kind in ("t", "k"):
        target = Image.new("RGB", tuple(pub["atlas"][0]), "white")
        regions = []
        for page in pub["pages"]:
            source_page = src.jpages[page["id"]]
            n, x, y, w, h = source_page["a"]
            _, ox, oy, ow, oh = page["a"]
            with Image.open(src.site / f"img/a/{kind}{n}.jpg") as original:
                target.paste(original.crop((x, y, x + w, y + h)), (ox, oy))
            regions.append({"page_id": page["id"], "source_region": source_page["a"], "output_region": page["a"]})
        buffer = io.BytesIO(); target.save(buffer, format="JPEG", quality=90)
        atlas_checks.append({"path": f"img/a/{kind}0.jpg", "regions": regions,
                             "sha256_from_only_declared_regions": hashlib.sha256(buffer.getvalue()).hexdigest(),
                             "pass": buffer.getvalue() == (out / f"img/a/{kind}0.jpg").read_bytes()})
    checks.append({"check": "atlas bytes reconstruct from only declared page regions",
                   "pass": all(c["pass"] for c in atlas_checks), "detail": atlas_checks})
    fonts = []
    for mime, raw in posting.iter_data_uris((out / "index.html").read_text()):
        if build_public.is_font(mime, raw):
            fonts.append({"mime": mime, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                          "metadata": build_public.run_font_tool("describe", raw),
                          "name_check": build_public.run_font_tool("check", raw)})
    return {"piece_id": pid, "selected_indices": indices,
            "selected_version_ids": [src.pieces[pid]["V"][i]["id"] for i in indices],
            "review_counts_for_selected_versions": counts,
            "corrected_lines_on_withheld_versions": posting.unpublished_corrections(src, db, pid, indices),
            "pages": result["pages"], "files": files, "images": images,
            "exposure": exposure, "checks": checks, "font_metadata": fonts,
            "reader_visible_audit": posting.audit_strings(out),
            "technical_exclusion_pass": all(c["pass"] is True for c in checks),
            "release_clearance": False}


def csv_file(path, rows, fields):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items() if k in fields})


def private_report(out, packet, queue, candidates, comparison):
    esc = lambda x: html.escape(str(x), quote=True)
    candidate = esc(packet["candidate"])
    selected = esc(", ".join(packet["preview"]["selected_version_ids"]))
    version_caveat = ("V[1] contains 16 corrected lines and shares a scan with p126."
                      if packet["candidate"] == "p001" else
                      "Inspect every proposed version and its image exposure before choosing it.")
    checks = "".join(f"<tr><td>{esc(c['check'])}</td><td>{'PASS' if c['pass'] else 'FAIL / unresolved'}</td></tr>" for c in packet["preview"]["checks"])
    rows = "".join(f"<tr><td>{esc(r['piece_id'])}</td><td>{esc(r['first_page'])}</td><td>{r['reviewed_lines']}/{r['total_lines']}</td><td>{esc(r['pool'] or 'unsorted')}</td><td>Pending</td></tr>" for r in candidates[:4])
    comparison_html = ""
    if comparison:
        b = comparison["exposure"]["withheld_blocks_visible"]
        labels = ", ".join(f"{x['page_id']} block {x['block']}" for x in b)
        preview_page = esc(packet["preview"]["pages"][0])
        comparison_html = f"""<section><h2>Alternate-version image exposure</h2>
<p>Adding the {esc(packet['candidate'])} version on diary62a also copies the page's remaining writing: {esc(labels)}.
Those blocks belong to p126 in the preserved catalog. Its release pool is unsorted. The shared-scan flag provides no clearance.</p>
<div class="compare"><figure><img src="preview/img/p/{preview_page}.jpg" alt="{preview_page} source scan"><figcaption>Current private preview: {preview_page}, {selected}. Read its image-exclusion result above.</figcaption></figure>
<figure><div class="scan"><img src="comparison-all-versions/img/p/diary62a.jpg" alt="diary62a source scan"><div class="region" style="top:78.68%;height:20.97%">p126 · withheld neighbour</div></div><figcaption>Private exposure demonstration: diary62a includes p001 V[1] and p126. The overlay follows the preserved line-box vertical extent (78.68–99.65%); it is not a crop or redaction. This image is not cleared.</figcaption></figure></div>
<p>Remedies for the author's choice: retain diary1 only; ask T02 for a reviewable derivative excluding p126 in every image tier and atlas (then recheck); or defer this version. Releasing the neighbour would require its own complete clearance. A CSS mask leaves the original bytes downloadable and is not a remedy.</p></section>"""
    # Technical report only. The reader itself remains the existing interface;
    # no generated editorial text is added to the work.
    document = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>T03 private release review</title><style>
body{{margin:0;background:#f6f3ec;color:#242b2c;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1120px;margin:auto;padding:38px 22px}}h1{{font:600 38px/1.15 Georgia,serif}}h2{{margin-top:34px}}.status{{padding:16px;border-left:5px solid #a34b21;background:#fff0dc}}.meta{{color:#56635d;font-size:14px}}a{{color:#245d50}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #d9dfda;vertical-align:top}}.compare{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}figure{{margin:0}}img{{width:100%;height:auto;display:block}}figcaption{{font-size:14px;padding:8px 0}}.scan{{position:relative}}.region{{position:absolute;bottom:1%;left:1%;right:1%;height:18%;border:3px solid #aa3029;color:#80221e;background:#ffeded55;font-size:14px;padding:5px;box-sizing:border-box}}code{{overflow-wrap:anywhere}}@media(max-width:650px){{.compare{{grid-template-columns:1fr}}main{{padding:24px 12px}}h1{{font-size:30px}}td,th{{padding:7px;font-size:14px}}}}</style></head><body><main>
<p class="meta">T03 · private technical preparation · {esc(packet['prepared_at'])}</p><h1>First-release review packet</h1>
<div class="status"><strong>Prepared for inspection. Release remains blocked.</strong><br>{candidate} and its selected version are derived candidates. No release classification, batch evidence, or author clearance has been invented. This whole packet contains withheld material and must stay private.</div>
<p><a href="preview/index.html">Open the bounded {candidate} reader preview</a> · <a href="packet.json">Exact checks and output inventory</a> · <a href="author-review-queue.json">Finite author-review queue</a> · <a href="proposed-whitelist.patch">Proposed whitelist diff (unapplied)</a></p>
<p class="meta">Tested source revision: <code>{esc(packet['tested_source_revision'])}</code>. All input hashes are in packet.json. Serve this folder on 127.0.0.1 so the reader can load its JSON; no hosted preview was deployed.</p>
<h2>Current first-release candidates, in recorded page order</h2><table><tr><th>Candidate</th><th>First page</th><th>Reviewed lines</th><th>Pool</th><th>Clearance</th></tr>{rows}</table>
<p>The full queue preserves source identifiers and page sequence. The separate 100-slot tracker assigns no publication numbers or dates. Weekly cadence begins only on an author-confirmed date after the gates are met.</p>
<h2>Decisions needed for this candidate</h2><ol><li>Confirm {candidate} for Series and choose {selected} or another explicitly reviewed version. {version_caveat}</li><li>Confirm the documented filed/registered workflow and supply the actual batch/deposit/evidence record before release. A database status is not filing evidence.</li><li>Review this exact preview, the downloadable font metadata, title and info-panel wording; confirm any permitted exposure.</li><li>Confirm the derived as-posted numbering and around-the-100 participation defaults when relevant. Select a first-post date only after clearance; past dates are historical.</li><li>Confirm Site versus social recording semantics before automation consumes publication flags.</li></ol>
<h2>Technical checks for the bounded preview</h2><table><tr><th>Check</th><th>Result</th></tr>{checks}</table>
{comparison_html}<h2>Review queue</h2><p>{len(queue)} finite records with stable source locators: uncertainty, line reviews, version choices, possible pairs, quotation/echo checks, flagged page visibility and pool classification. Categories describe pending work, not editorial judgments.</p>
<h2>Scope</h2><p>The preview reuses the existing reader and PR #101 builder. No source scan, transcript, studio record, public whitelist, account or deployment was changed. noindex is retained; it is an indexing directive, not access control.</p></main></body></html>"""
    (out / "index.html").write_text(document)


def prepare(source, database, candidate, output):
    source, database, output = Path(source).resolve(), Path(database).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError("Output must be a new directory; existing artifacts are never overwritten.")
    for protected in [source / "site", source / "studio", source / "exports", database, source / ".git"]:
        if output == protected or protected in output.parents or output in protected.parents:
            raise ValueError("Output overlaps source or database inputs.")
    src, db = posting.Source(source), posting.load_db(database)
    if candidate not in src.pieces:
        raise ValueError("Unknown candidate: " + candidate)
    if src.public:
        raise ValueError("This first-release packet requires the preserved empty whitelist; use the posting workflow for an existing release.")
    before = source_inputs(src, posting.find_db_root(database))
    output.mkdir(parents=True)
    idx, basis, notes = posting.select_versions(src, db, candidate, False)
    gated_command = [sys.executable, str(source / "tools/post_poem.py"), candidate,
                     "--source", str(source), "--db", str(database), "--dry-run",
                     "--workdir", str(output / "gated-dry-run")]
    run = subprocess.run(gated_command, capture_output=True, text=True, timeout=180)
    (output / "gated-dry-run.txt").write_text(run.stdout + run.stderr)
    # No --force, made-up database rows or acceptances. Building an isolated
    # private inspection artifact does not change or satisfy the posting gates.
    preview = audit_preview(src, db, candidate, idx, output / "preview")
    comparison = None
    if candidate == "p001" and len(src.pieces[candidate]["V"]) == 2:
        comparison = audit_preview(src, db, candidate, [0, 1], output / "comparison-all-versions")
        write_json(output / "comparison-exposure.json", comparison)
    queue = author_queue(src, db)
    candidates = catalog(src, db)
    write_json(output / "author-review-queue.json", queue)
    write_json(output / "source-catalog.json", candidates)
    csv_file(output / "first-release-queue.csv", candidates[:4],
             ["piece_id", "first_page", "page_sequence", "recorded_kind", "recorded_status", "pool", "preview_version_ids", "preview_selection_basis", "reviewed_lines", "total_lines", "batch_gate"])
    csv_file(output / "release-tracker-100-slots.csv",
             [{"planning_slot": n, "assigned_number": "", "piece_id": "", "status": "unassigned", "confirmed_date": "", "public_url": ""} for n in range(1, 101)],
             ["planning_slot", "assigned_number", "piece_id", "status", "confirmed_date", "public_url"])
    proposed = {"pieces": [candidate]}
    import difflib
    old = src.release_path.read_text()
    patch = "".join(difflib.unified_diff(old.splitlines(True), (json.dumps(proposed, indent=2) + "\n").splitlines(True),
                                         "a/release/public.json", "b/release/public.json"))
    (output / "proposed-whitelist.patch").write_text(patch)
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    code_paths = ["tools/prepare_release_packet.py", "tools/post_poem.py", "tools/build_public.py", "tools/font_rename.py"]
    code_hashes = {p: digest(source / p) for p in code_paths}
    after = source_inputs(src, posting.find_db_root(database))
    if before != after:
        raise ValueError("Input bytes changed while preparing; packet is not a stable observation.")
    relative_inputs = {}
    for path, sha in before.items():
        p = Path(path)
        relative_inputs[str(p.relative_to(source)) if source in p.parents else str(p)] = sha
    packet = {"schema": "versforms.release-preparation.v1", "prepared_at": dt.datetime.now(dt.timezone.utc).isoformat(),
              "status": "private-preparation-only", "release_clearance": False,
              "repository": "4444J99/journal-handwritten-web", "tested_source_revision": revision,
              "code_sha256": code_hashes, "input_sha256": relative_inputs,
              "candidate": candidate, "candidate_authority": "derived; awaiting author confirmation",
              "candidate_source": SOURCE_RECORD if candidate == "p001" else "Caller-selected inspection candidate; recorded page order in studio/data/review.json; no approval inferred",
              "preview_selection_basis": basis, "selection_notes": notes,
              "database_documents": {k: len(v) for k, v in db.items()},
              "gates": {"series": dict(zip(("pass", "detail"), posting.gate_series(db, candidate))),
                        "all_versions_reviewed": dict(zip(("pass", "detail"), posting.gate_verified(src, db, candidate))),
                        "filed_or_registered_status": dict(zip(("pass", "detail"), posting.gate_filed(db, candidate))),
                        "filing_evidence": {"pass": False, "detail": "No independent filing evidence supplied or verified by this command."},
                        "author_release_clearance": {"pass": False, "detail": "Preparation never grants release authority."}},
              "actual_gated_dry_run": {"argv": gated_command, "exit_code": run.returncode,
                                      "public_repo_checks": "not run: no public clone supplied", "log": "gated-dry-run.txt"},
              "preview": preview, "queue_categories": dict(collections.Counter(r["category"] for r in queue)),
              "queue_records": len(queue), "inputs_unchanged": before == after,
              "proposal": {"whitelist": proposed, "applied": False, "first_post_date": None,
                           "cadence_days": 7, "schedule_basis": "author-confirmed start after clearance; no commitment"},
              "limits": ["Preserved export snapshot; no live database freshness claimed.",
                         "Catalogued exclusion plus private visual inspection; no independent original archival recovery claim.",
                         "No physical phone test, deployment or filing performed.",
                         "Private shared context packet 2026-10-16-v1.1 / projection r2 was inaccessible."]}
    write_json(output / "packet.json", packet)
    private_report(output, packet, queue, candidates, comparison)
    write_json(output / "files.json", inventory(output))
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--db", type=Path, default=ROOT / "exports/studio-db-2026-11-05")
    parser.add_argument("--candidate", default="p001")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        packet = prepare(args.source, args.db, args.candidate, args.out)
    except (ValueError, OSError, posting.Stop, subprocess.SubprocessError) as exc:
        print("Preparation failed: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps({"status": packet["status"], "release_clearance": False,
                      "candidate": packet["candidate"], "gated_dry_run_exit": packet["actual_gated_dry_run"]["exit_code"],
                      "bounded_preview_checks_pass": packet["preview"]["technical_exclusion_pass"],
                      "queue_records": packet["queue_records"], "out": str(args.out)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
