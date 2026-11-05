#!/usr/bin/env python3
"""Export the review studio's documents from D1 to the per-document layout (stdlib only).

The reverse of import_export.py. It writes the same layout as exports/studio-db-2026-11-05:
COLLECTION/DOCID.json, one JSON document per file (2-space indent, UTF-8 not escaped,
one trailing newline, keys in stored order), no folder for an empty collection, plus a
README.md with per-collection counts.

Sources (give exactly one):

  --from-json FILE    the output of
                          wrangler d1 execute object-lessons-submissions --remote --json \\
                            --command "SELECT collection, id, data FROM vf_docs ORDER BY collection, id" > FILE
                      (a list of result objects, one result object, or a bare list of rows)
  --local PERSIST_DIR a local wrangler D1 persist directory (the one given to
                      `wrangler pages dev --persist-to` / `wrangler d1 execute --local --persist-to`).
                      The SQLite file holding vf_docs is opened read-only.

    python3 studio-cf/export_db.py --from-json docs.json --dry-run
    python3 studio-cf/export_db.py --from-json docs.json --out exports/studio-db-DATE
    python3 studio-cf/export_db.py --local PERSIST_DIR --out /path/outside/repo/export

--dry-run   print per-collection counts and rejects only; write nothing.
--out DIR   write the export. DIR must not exist or must be empty; nothing is ever
            overwritten or deleted.

Only vf_docs is read (the database is shared with another project; sqlguard.py checks
the query). This script never talks to Cloudflare. Rows that fail validation (unknown
collection, bad id, not a JSON object, over 64 KiB) are listed as rejects and block
writing unless --skip-rejects.
"""
import argparse
import json
import re
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sqlguard  # noqa: E402
from import_export import COLLECTIONS, DOC_ID_RE, MAX_DOC_BYTES, DB_NAME, Reject, NonStandardJSON, compact_size, loads_strict  # noqa: E402

QUERY = "SELECT collection, id, data FROM vf_docs ORDER BY collection, id"


def remote_command():
    """The exact command for the author to run (printed by --help text and by the README)."""
    sqlguard.check(QUERY)
    return f'wrangler d1 execute {DB_NAME} --remote --json --command "{QUERY}"'


def rows_from_wrangler_json(text):
    """Accepts the shapes `wrangler d1 execute --json` produces. Returns a list of row dicts."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise SystemExit(f"not valid JSON: {e.msg} at line {e.lineno}")
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise SystemExit("unexpected JSON: expected a list of results or rows")
    rows = []
    for item in parsed:
        if isinstance(item, dict) and "results" in item:
            if item.get("success") is False:
                raise SystemExit("the wrangler result reports success: false")
            res = item["results"]
            if not isinstance(res, list):
                raise SystemExit("unexpected JSON: results is not a list")
            rows.extend(res)
        elif isinstance(item, dict):
            rows.append(item)
        else:
            raise SystemExit("unexpected JSON: an element is neither a result nor a row")
    return rows


def rows_from_persist_dir(persist):
    """Reads vf_docs read-only from the SQLite file in a wrangler persist directory."""
    sqlguard.check(QUERY)
    root = Path(persist)
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    found = []
    for f in sorted(root.rglob("*.sqlite")):
        if f.name == "metadata.sqlite":
            continue
        try:
            conn = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            has = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='vf_docs'").fetchone()
            if has:
                rows = [{"collection": c, "id": i, "data": d} for c, i, d in conn.execute(QUERY)]
                found.append((f, rows))
        except sqlite3.Error:
            pass
        finally:
            conn.close()
    if not found:
        raise SystemExit(f"no SQLite file with a vf_docs table under {root}")
    if len(found) > 1:
        raise SystemExit("more than one SQLite file has a vf_docs table: " + ", ".join(str(f) for f, _ in found))
    return found[0][1]


def collect(rows):
    """Validates rows. Returns (docs {collection: {id: data}}, rejects)."""
    docs = {c: {} for c in COLLECTIONS}
    rejects = []
    seen = set()
    for n, row in enumerate(rows, 1):
        if not isinstance(row, dict) or not {"collection", "id", "data"} <= set(row):
            rejects.append(Reject(f"row {n}", "missing collection, id or data"))
            continue
        coll, doc_id, raw = row["collection"], row["id"], row["data"]
        label = f"{coll}/{doc_id}" if isinstance(coll, str) and isinstance(doc_id, str) else f"row {n}"
        if coll not in COLLECTIONS:
            rejects.append(Reject(label, "unknown collection"))
            continue
        if not isinstance(doc_id, str) or not DOC_ID_RE.fullmatch(doc_id) or doc_id in (".", ".."):
            rejects.append(Reject(label, "invalid document id"))
            continue
        if (coll, doc_id) in seen:
            rejects.append(Reject(label, "duplicate document"))
            continue
        try:
            data = loads_strict(raw) if isinstance(raw, str) else raw
        except NonStandardJSON:
            rejects.append(Reject(label, "data contains NaN or Infinity, which JSON cannot hold"))
            continue
        except json.JSONDecodeError:
            rejects.append(Reject(label, "data is not valid JSON"))
            continue
        if not isinstance(data, dict):
            rejects.append(Reject(label, "data is not a JSON object"))
            continue
        # measured the way the API measures a document (compact JSON); the pretty-printed file is larger and
        # must not decide, or a document the API accepts would block the whole export
        try:
            size = compact_size(data)
        except ValueError:
            rejects.append(Reject(label, "data contains a number JSON cannot hold (NaN, Infinity or beyond the double range)"))
            continue
        if size > MAX_DOC_BYTES:
            rejects.append(Reject(label, f"larger than {MAX_DOC_BYTES} bytes ({size} compact)"))
            continue
        seen.add((coll, doc_id))
        docs[coll][doc_id] = data
    return docs, rejects


def render(data):
    """One document file: the format of the PR 73 export, byte for byte."""
    return json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def readme_text(docs, date):
    lines = [
        f"# Review studio database export — {date}",
        "",
        "Exported from the Cloudflare D1 table `vf_docs`, one JSON file per document.",
        "",
        "| Collection | Documents |",
        "|---|---|",
    ]
    for c in COLLECTIONS:
        lines.append(f"| {c} | {len(docs[c])} |")
    lines += ["", "Empty collections have no folder. Use this as the input for `import_export.py` (`--dry-run` first).", ""]
    return "\n".join(lines)


def report(docs, rejects, out):
    total = 0
    for c in COLLECTIONS:
        total += len(docs[c])
        print(f"{c:<10} {len(docs[c])}", file=out)
    print(f"{'total':<10} {total}", file=out)
    print(f"rejects    {len(rejects)}", file=out)
    for r in rejects:
        print(f"  REJECT {r}", file=out)


def write_export(docs, out_dir, date):
    out = Path(out_dir)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise SystemExit(f"refusing to write into {out}: it exists and is not an empty directory")
    out.mkdir(parents=True, exist_ok=True)
    for c in COLLECTIONS:
        if not docs[c]:
            continue
        (out / c).mkdir()
        for doc_id in sorted(docs[c]):
            (out / c / f"{doc_id}.json").write_bytes(render(docs[c][doc_id]).encode("utf-8"))
    (out / "README.md").write_text(readme_text(docs, date), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-json", metavar="FILE", help="output of wrangler d1 execute --json on vf_docs")
    src.add_argument("--local", metavar="PERSIST_DIR", help="local wrangler D1 persist directory")
    ap.add_argument("--out", metavar="DIR", help="write the export here (must not exist or be empty)")
    ap.add_argument("--dry-run", action="store_true", help="print counts and rejects only")
    ap.add_argument("--skip-rejects", action="store_true", help="write the valid documents even when some rows were rejected")
    ap.add_argument("--date", help="date in the README heading (default: today, UTC)")
    args = ap.parse_args(argv)
    if not (args.dry_run or args.out):
        ap.error("nothing to do: give --dry-run or --out DIR")

    if args.from_json:
        p = Path(args.from_json)
        if not p.is_file():
            raise SystemExit(f"not a file: {p}")
        rows = rows_from_wrangler_json(p.read_text(encoding="utf-8"))
    else:
        rows = rows_from_persist_dir(args.local)

    docs, rejects = collect(rows)
    report(docs, rejects, sys.stdout)
    if args.dry_run:
        return 1 if rejects else 0
    if rejects and not args.skip_rejects:
        print("refusing to write with rejects present (use --skip-rejects to write the valid documents)", file=sys.stderr)
        return 1
    date = args.date or time.strftime("%Y-%m-%d", time.gmtime())
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", date):
        raise SystemExit("--date must look like 2026-11-05")
    write_export(docs, args.out, date)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
