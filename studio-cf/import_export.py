#!/usr/bin/env python3
"""Import a review-studio export into the D1 database (stdlib only).

Input is an export directory with one JSON file per document at
COLLECTION/ID.json (the format of exports/studio-db-2026-11-05). Each file holds
the document's data object exactly as the page stored it; the file name (minus
.json) is the document id.

    python3 studio-cf/import_export.py EXPORT_DIR --dry-run
    python3 studio-cf/import_export.py EXPORT_DIR --sql-out import.sql
    python3 studio-cf/import_export.py EXPORT_DIR --local PERSIST_DIR
    python3 studio-cf/import_export.py EXPORT_DIR --sql-out import.sql --remote

--dry-run   validate and print per-collection counts and rejects; write nothing.
--sql-out   write idempotent SQL: schema, collection revs and document writes.
            The six legacy collections replace matching IDs. Notes and
            contributions preserve matching revisions and reject collisions.
--local DIR apply to the local wrangler D1 simulation persisted in DIR
            (wrangler d1 execute --local). Never touches Cloudflare.
--remote    only PRINTS the command for the author to run; it is never executed
            by this script.

The target database (object-lessons-submissions) is shared with another project, so all
studio tables are prefixed vf_ and sqlguard.py refuses to emit, write or apply any SQL
that touches a non-vf_ object (checked in build_sql, before --sql-out/--local/--remote).

Nothing here talks to Cloudflare. Rejects (bad collection, bad id, too large,
not a JSON object, ...) are listed and block writing unless --skip-rejects.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sqlguard  # noqa: E402

COLLECTIONS = ("reviews", "decisions", "versions", "release", "batches", "rconfig", "notes", "contributions", "artifacts", "publish")
IMMUTABLE_COLLECTIONS = ("notes", "contributions", "artifacts")
COLLISION_SAFE_COLLECTIONS = IMMUTABLE_COLLECTIONS + ("publish",)
DOC_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
MAX_DOC_BYTES = 64 * 1024  # the API's limit on a document, measured on its compact JSON (see compact_size)
MAX_FILE_BYTES = 8 * MAX_DOC_BYTES  # sanity cap on what is read at all; a pretty-printed file is larger than its stored form
DB_NAME = "object-lessons-submissions"
DEFAULT_WRANGLER = "/opt/homebrew/bin/wrangler"


class Reject:
    def __init__(self, path, reason):
        self.path, self.reason = path, reason

    def __str__(self):
        return f"{self.path}: {self.reason}"


class NonStandardJSON(ValueError):
    """NaN, Infinity or -Infinity: Python's json accepts them, JSON (and the API's JSON.parse) does not."""


def _reject_constant(name):
    raise NonStandardJSON(name)


def loads_strict(text):
    """json.loads that refuses NaN, Infinity and -Infinity. One such stored row would make the API's
    JSON.parse fail for every read of its whole collection."""
    return json.loads(text, parse_constant=_reject_constant)


def compact_json(data):
    """The compact form the API stores. Raises ValueError for NaN or Infinity, which also catches a number such
    as 1e999 that Python reads as infinity and would write back as the invalid text 'Infinity'."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def compact_size(data):
    """Size in bytes of the document as the API measures it (its compact JSON, UTF-8), not of a pretty-printed file."""
    return len(compact_json(data).encode("utf-8"))


def valid_revision(collection, doc_id, data):
    """Minimum persistence envelope. The studio model validates the full record."""
    family = {"notes": "note", "contributions": "contribution", "artifacts": "artifact"}.get(collection)
    def valid_id(value):
        return isinstance(value, str) and DOC_ID_RE.fullmatch(value) and value not in (".", "..")
    parents = data.get("parents")
    return (type(data.get("schemaVersion")) is int and data["schemaVersion"] == 1
            and data.get("family") == family and data.get("revisionId") == doc_id
            and valid_id(data.get("recordId")) and isinstance(parents, list)
            and all(valid_id(p) and p != doc_id for p in parents)
            and len(set(parents)) == len(parents))


def scan(export_dir):
    """Returns (docs, rejects). docs: {collection: {id: data}} for every collection."""
    root = Path(export_dir)
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")
    docs = {c: {} for c in COLLECTIONS}
    rejects = []
    for entry in sorted(root.iterdir(), key=lambda p: p.name):
        if entry.is_file() and entry.suffix.lower() in (".md", ".txt"):
            continue  # README and notes beside the collections
        if entry.is_symlink() or not entry.is_dir():
            rejects.append(Reject(entry.name, "not a collection directory"))
            continue
        if entry.name not in COLLECTIONS:
            rejects.append(Reject(entry.name + "/", "unknown collection"))
            continue
        for f in sorted(entry.iterdir(), key=lambda p: p.name):
            rel = f"{entry.name}/{f.name}"
            if f.is_symlink() or not f.is_file():
                rejects.append(Reject(rel, "not a regular file"))
                continue
            if f.suffix != ".json":
                rejects.append(Reject(rel, "not a .json file"))
                continue
            doc_id = f.name[: -len(".json")]
            if not DOC_ID_RE.fullmatch(doc_id) or doc_id in (".", ".."):
                rejects.append(Reject(rel, "invalid document id"))
                continue
            raw = f.read_bytes()
            if len(raw) > MAX_FILE_BYTES:
                rejects.append(Reject(rel, f"larger than {MAX_FILE_BYTES} bytes as a file ({len(raw)})"))
                continue
            try:
                data = loads_strict(raw.decode("utf-8"))
            except NonStandardJSON:
                rejects.append(Reject(rel, "contains NaN or Infinity, which JSON cannot hold"))
                continue
            except ValueError as e:  # UnicodeDecodeError and json.JSONDecodeError
                rejects.append(Reject(rel, f"not valid UTF-8 JSON ({type(e).__name__})"))
                continue
            if not isinstance(data, dict):
                rejects.append(Reject(rel, "top level is not a JSON object"))
                continue
            if entry.name in IMMUTABLE_COLLECTIONS and not valid_revision(entry.name, doc_id, data):
                rejects.append(Reject(rel, "invalid immutable revision envelope"))
                continue
            try:
                size = compact_size(data)
            except ValueError:
                rejects.append(Reject(rel, "contains a number JSON cannot hold (NaN, Infinity or beyond the double range)"))
                continue
            if size > MAX_DOC_BYTES:
                rejects.append(Reject(rel, f"larger than {MAX_DOC_BYTES} bytes once compacted ({size})"))
                continue
            docs[entry.name][doc_id] = data
    return docs, rejects


def sql_string(s):
    """A SQL string literal. Single quotes are doubled; NUL is impossible after JSON escaping."""
    if "\x00" in s:
        raise ValueError("NUL in string")
    return "'" + s.replace("'", "''") + "'"


def same_json_sql(left, right):
    """Structural JSON equality, independent of object order/Unicode escaping.

    json_tree reads only the supplied JSON values. Container nodes retain type;
    leaves retain their full path, type and value, including array order.
    JSON numbers compare numerically, as they do after the API's JSON.parse.
    """
    def tree(value):
        return ("SELECT fullkey, CASE WHEN type IN ('integer', 'real') THEN 'number' ELSE type END, atom "
                f"FROM json_tree({value})")
    a, b = tree(left), tree(right)
    return f"NOT EXISTS ({a} EXCEPT {b}) AND NOT EXISTS ({b} EXCEPT {a})"


def build_sql(docs, now, include_schema=True):
    parts = []
    if include_schema:
        parts.append((HERE / "schema.sql").read_text())
    parts.append(f"-- review studio import, {sum(len(v) for v in docs.values())} documents")
    for coll in COLLECTIONS:
        items = docs.get(coll) or {}
        if not items:
            continue
        c = sql_string(coll)
        if coll in COLLISION_SAFE_COLLECTIONS:
            for doc_id, data in items.items():
                if coll in IMMUTABLE_COLLECTIONS and not valid_revision(coll, doc_id, data):
                    raise ValueError(f"invalid immutable revision envelope: {coll}/{doc_id}")
            ids = ", ".join(sql_string(doc_id) for doc_id in sorted(items))
            absent = f"(SELECT count(*) FROM vf_docs WHERE collection = {c} AND id IN ({ids})) < {len(items)}"
            parts.append(f"INSERT INTO vf_revs (collection, rev) SELECT {c}, 1 WHERE {absent} ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;")
        else:
            parts.append(f"INSERT INTO vf_revs (collection, rev) VALUES ({c}, 1) ON CONFLICT(collection) DO UPDATE SET rev = rev + 1;")
        for doc_id in sorted(items):
            # ensure_ascii keeps the statement pure ASCII with no raw newlines
            text = json.dumps(items[doc_id], ensure_ascii=True, separators=(",", ":"), allow_nan=False)
            values = f"({c}, {sql_string(doc_id)}, {sql_string(text)}, {sql_string(now)}, (SELECT rev FROM vf_revs WHERE collection = {c}))"
            if coll in COLLISION_SAFE_COLLECTIONS:
                # A differing same-ID revision violates data's existing NOT NULL
                # constraint and aborts this statement; it never replaces history.
                # An identical retry retains original data, updated_at and rev.
                parts.append("INSERT INTO vf_docs (collection, id, data, updated_at, rev) VALUES " + values
                             + " ON CONFLICT(collection, id) DO UPDATE SET data = CASE WHEN "
                             + same_json_sql("vf_docs.data", "excluded.data") + " THEN vf_docs.data ELSE NULL END;")
            else:
                parts.append("INSERT OR REPLACE INTO vf_docs (collection, id, data, updated_at, rev) VALUES " + values + ";")
    sql = "\n".join(parts) + "\n"
    # The database is shared with another project: refuse anything that is not a vf_ object.
    sqlguard.check(sql)
    return sql


def report(docs, rejects, out):
    total = 0
    for c in COLLECTIONS:
        n = len(docs[c])
        total += n
        print(f"{c:<10} {n}", file=out)
    print(f"{'total':<10} {total}", file=out)
    print(f"rejects    {len(rejects)}", file=out)
    for r in rejects:
        print(f"  REJECT {r}", file=out)


def wrangler_cmd(args, extra):
    exe = args.wrangler or (DEFAULT_WRANGLER if os.path.exists(DEFAULT_WRANGLER) else shutil.which("wrangler"))
    if not exe:
        raise SystemExit("wrangler not found; pass --wrangler PATH")
    return [exe, "d1", "execute", DB_NAME, *extra]


def run_local(args, sql_path, persist):
    """wrangler d1 execute --local. wrangler 4.104 prints its result and then does not exit
    under this host's Node, so the process is stopped once it has reported success."""
    persist = Path(persist).resolve()
    persist.mkdir(parents=True, exist_ok=True)
    cmd = wrangler_cmd(args, ["--local", "--persist-to", str(persist), "--cwd", str(HERE), "--file", str(sql_path)])
    env = dict(os.environ)
    env.setdefault("WRANGLER_SEND_METRICS", "false")
    # keep miniflare from fetching workers.cloudflare.com/cf.json and caching it in the repo
    env.setdefault("CLOUDFLARE_CF_FETCH_ENABLED", "false")
    env.setdefault("WRANGLER_LOG_PATH", str(persist.parent / "wrangler-logs"))
    env.setdefault("XDG_CONFIG_HOME", str(persist.parent / "wrangler-xdg"))
    env.setdefault("CI", "1")
    proc = subprocess.Popen(cmd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out, deadline, ok = [], time.time() + args.timeout, False
    # Watchdog: also ends wrangler if it hangs without printing anything.
    watchdog = threading.Timer(args.timeout, lambda: proc.poll() is None and proc.kill())
    watchdog.daemon = True
    watchdog.start()
    try:
        for line in proc.stdout:
            out.append(line)
            joined = "".join(out)
            if re.search(r"commands? executed successfully", joined) and joined.rstrip().endswith("]"):
                ok = True
                break
            if time.time() > deadline:
                break
        if not ok:
            code = proc.wait(timeout=5) if proc.poll() is not None else None
            ok = code == 0
    finally:
        watchdog.cancel()
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    if not ok:
        raise SystemExit("wrangler d1 execute --local failed:\n" + "".join(out))
    return "".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export_dir")
    ap.add_argument("--dry-run", action="store_true", help="validate and print counts only")
    ap.add_argument("--sql-out", metavar="FILE", help="write the import SQL here")
    ap.add_argument("--local", metavar="PERSIST_DIR", help="apply to the local wrangler D1 simulation persisted in this directory")
    ap.add_argument("--remote", action="store_true", help="print the command to run against the real database (needs --sql-out); never executes it")
    ap.add_argument("--skip-rejects", action="store_true", help="write/apply the valid documents even when some files were rejected")
    ap.add_argument("--no-schema", action="store_true", help="leave the CREATE TABLE statements out of the SQL")
    ap.add_argument("--now", help="updated_at value (default: current UTC time)")
    ap.add_argument("--wrangler", help="path to wrangler (default /opt/homebrew/bin/wrangler, else PATH)")
    ap.add_argument("--timeout", type=int, default=120, help="seconds to wait for wrangler --local")
    args = ap.parse_args(argv)

    if not (args.dry_run or args.sql_out or args.local or args.remote):
        ap.error("nothing to do: give --dry-run, --sql-out, --local or --remote")
    if args.remote and not args.sql_out:
        ap.error("--remote needs --sql-out (the file the printed command refers to)")

    docs, rejects = scan(args.export_dir)
    report(docs, rejects, sys.stdout)

    if args.dry_run and not (args.sql_out or args.local or args.remote):
        return 1 if rejects else 0
    if rejects and not args.skip_rejects:
        print("refusing to write with rejects present (use --skip-rejects to proceed with the valid documents)", file=sys.stderr)
        return 1

    now = args.now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        sql = build_sql(docs, now, include_schema=not args.no_schema)
    except sqlguard.SqlGuardError as e:
        print(str(e), file=sys.stderr)
        return 1

    sql_path = None
    if args.sql_out:
        sql_path = Path(args.sql_out)
        sql_path.write_text(sql, encoding="ascii")
        print(f"wrote {sql_path} ({len(sql)} bytes)")

    if args.local:
        tmp = None
        if sql_path is None:
            persist_parent = Path(args.local).resolve().parent
            persist_parent.mkdir(parents=True, exist_ok=True)
            fd, name = tempfile.mkstemp(suffix=".sql", prefix="studio-import-", dir=persist_parent)
            os.close(fd)
            tmp = sql_path = Path(name)
            sql_path.write_text(sql, encoding="ascii")
        try:
            run_local(args, sql_path, args.local)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
        print(f"applied to local D1 in {args.local}")

    if args.remote:
        print("\nNOT executed. When the Cloudflare Access policy is confirmed, run:\n")
        print(f"  wrangler d1 execute {DB_NAME} --remote --cwd {HERE} --file={sql_path.resolve()}\n")
        print("If wrangler does not find its login, put `env -u XDG_CONFIG_HOME` in front (README step 10).\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
