#!/usr/bin/env python3
"""Post a poem: gate it, build the public site for it, and prepare a pull request.

    python3 tools/post_poem.py PIECE_ID [PIECE_ID ...] --db EXPORT_DIR [--public-repo PATH]
        [--include-versions] [--force] [--accept-shared-scan IDS] [--accept-embedded-font]
        [--dry-run] [--no-pr]

The public repository (4444J99/versforms) is only ever changed through a pull request that
this script prepares and the author merges. See docs/posting.md.

Exit codes
    0  done (or dry run complete)
    2  a gate failed (Series, fully verified, filed batch); --force overrides these three only
    3  a hard stop; --force never overrides these:
         own pool is reserve or archive, shared scan (including the facing page of a spread
         image), stale transcript, unknown piece id, public repository preconditions,
         embedded font not accepted, output checks
    64 usage error
    1  an operation failed part-way (git, gh); the message says what state was left

stdlib and Pillow only. Poem text is never printed, logged, or put in a commit or PR body.
"""
import argparse, difflib, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import build_public  # noqa: E402

PUBLIC_REPO_NAME = "4444J99/versforms"
COLLECTIONS = ("reviews", "decisions", "versions", "release", "batches", "rconfig")
POOLS = ("series", "reserve", "archive")
PLACEHOLDER = "[[quoted passage:]]"
# the author's music; built from parts so this file is not itself a hit
OLD_NAME_RE = re.compile("etceter" + "4", re.I)
EXIT_OK, EXIT_PARTIAL, EXIT_GATE, EXIT_STOP, EXIT_USAGE = 0, 1, 2, 3, 64


class Stop(Exception):
    """A hard stop raised while loading inputs."""


def say(msg=""):
    print(msg, flush=True)


# ------------------------------------------------------------------ inputs

class Source:
    """The private repository's published data plus the studio's review data."""

    def __init__(self, root):
        self.root = Path(root)
        self.site = self.root / "site"
        try:
            self.j = json.loads((self.site / "data" / "j.json").read_text())
            self.review = json.loads((self.root / "studio" / "data" / "review.json").read_text())
        except (OSError, ValueError) as e:
            raise Stop(f"cannot read site/data/j.json or studio/data/review.json under {self.root}: {e}")
        self.pieces = {p["id"]: p for p in self.j["pieces"]}
        self.jpages = {p["id"]: p for p in self.j["pages"]}
        self.items = {i["id"]: i for i in self.review["items"]}
        self.rpages = {p["id"]: p for p in self.review["pages"]}
        self.release_path = self.root / "release" / "public.json"
        rel = build_public.load_release(self.release_path)
        self.public = list(dict.fromkeys(rel.get("pieces", [])))
        self.all_versions = list(dict.fromkeys(rel.get("all_versions", [])))

    def item_line_ids(self, pid):
        """Every line id of every version block of the piece, per the review data (None: no item)."""
        item = self.items.get(pid)
        if item is None:
            return None
        ids = []
        for v in item["versions"]:
            for b in v["blocks"]:
                ids.extend(l["id"] for l in self.rpages[v["page"]]["blocks"][b]["lines"])
        return ids

    def pages_of(self, pid, indices):
        return sorted({pg for i in indices for pg, _ in self.pieces[pid]["V"][i]["P"]})

    def spread_mates(self, pages):
        """Pages whose scan shares a spread image file with one of `pages`.

        The build copies img/s/{sp.f}.jpg for every published page that has sp.f. That file is the
        whole two-page spread, so whatever is written on the other page of the spread is in the
        downloaded image. The spread file of a page is its sp.f; the other page of the spread is
        found by the same sp.k (spread key) or the same sp.f, or by being the page the file is named after."""
        pages = set(pages)
        mates = set()
        for pg in pages:
            sp = self.jpages[pg].get("sp") or {}
            f, k = sp.get("f"), sp.get("k")
            if not f:
                continue
            for q in self.j["pages"]:
                s2 = q.get("sp") or {}
                if q["id"] != pg and ((k and s2.get("k") == k) or s2.get("f") == f or q["id"] == f):
                    mates.add(q["id"])
        return sorted(mates - pages)

    def published_blocks(self, pid, indices):
        return sorted({(pg, b) for i in indices for pg, bl in self.pieces[pid]["V"][i]["P"] for b in bl})


def find_db_root(path):
    base = Path(path)
    if not base.is_dir():
        raise Stop(f"--db {path} is not a directory")
    if any((base / c).is_dir() for c in COLLECTIONS):
        return base
    nested = sorted(p for p in base.glob("exports/*") if any((p / c).is_dir() for c in COLLECTIONS))
    if len(nested) == 1:
        return nested[0]
    return base  # an export whose collections are all empty has no folders


def load_db(path):
    """{collection: {doc id: doc}} from EXPORT_DIR/COLLECTION/DOCID.json."""
    root = find_db_root(path)
    db = {c: {} for c in COLLECTIONS}
    for c in COLLECTIONS:
        folder = root / c
        if not folder.is_dir():
            continue
        for f in sorted(folder.glob("*.json")):
            try:
                doc = json.loads(f.read_text())
            except ValueError as e:
                raise Stop(f"{f}: not valid JSON ({e})")
            if isinstance(doc, dict):
                db[c][f.stem] = doc
    return db


# ------------------------------------------------------------------ gates

def gate_series(db, pid):
    doc = db["release"].get(pid)
    if doc is None:
        return False, "no release document (unsorted)"
    pool = doc.get("pool")
    return pool == "series", f"pool is {pool!r}" if pool != "series" else "pool is 'series'"


def gate_verified(src, db, pid):
    ids = src.item_line_ids(pid)
    if ids is None:
        return False, "no review item for this piece"
    bad = []
    for lid in ids:
        doc = db["reviews"].get(lid)
        ok = doc is not None and (doc.get("status") == "confirmed" or (doc.get("status") == "corrected" and isinstance(doc.get("text"), str)))
        if not ok:
            bad.append(lid)
    if bad:
        return False, f"{len(bad)} of {len(ids)} lines not confirmed or corrected (first: {', '.join(bad[:8])})"
    return True, f"all {len(ids)} lines confirmed or corrected"


def gate_filed(db, pid):
    for bid, b in sorted(db["batches"].items()):
        if pid in (b.get("items") or []):
            ok = b.get("status") in ("filed", "registered")
            return ok, f"batch {bid} is {b.get('status')!r}"
    return False, "not listed in any batch"


# ------------------------------------------------------------------ versions and corrections

def final_decision_pieces(src):
    """Piece that each '...-final' decision key is about (the studio hard-codes the same lookup)."""
    out = {}
    for pid, p in src.pieces.items():
        pages = {pg for v in p["V"] for pg, _ in v["P"]}
        if {"diary53", "diary54"} <= pages:
            out["nothing-shines-final"] = pid
    return out


def select_versions(src, db, pid, include_versions):
    """-> (indices into V, how it was chosen, notes). Final decided by the author, else the top of the stack."""
    pc = src.pieces[pid]
    n = len(pc["V"])
    notes = []
    if include_versions:
        return list(range(n)), "whole stack (--include-versions)", notes
    found = set()
    for key, doc in db["decisions"].items():
        if not key.endswith("-final"):
            continue
        choice = doc.get("choice")
        if not isinstance(choice, str) or not choice:
            continue
        if choice == "layers":
            if final_decision_pieces(src).get(key) == pid:
                notes.append("the author chose 'keep drafts as layers' for this piece; publishing the top of the stack only. Use --include-versions once the author approves the layers")
            continue
        for vi, v in enumerate(pc["V"]):
            if any(choice == f"{pg}-{b}" for pg, bl in v["P"] for b in bl):
                found.add(vi)
    if len(found) > 1:
        raise Stop(f"{pid}: final-version decisions name more than one version ({sorted(found)}); the author must settle it in the studio")
    if found:
        return [found.pop()], "decided final", notes
    return [pc["top"]], "top of the stack; no decided final", notes


def load_corrections(src, db, pid, indices):
    """-> (corrections {(page, block, line): text}, counts, stale line ids) for the published blocks."""
    corr, stale = {}, []
    counts = {"confirmed": 0, "corrected": 0, "unreviewed": 0}
    for pg, bi in src.published_blocks(pid, indices):
        for li, current in enumerate(src.jpages[pg]["B"][bi]["L"]):
            lid = f"{pg}-{bi}-{li}"
            doc = db["reviews"].get(lid)
            if doc is None:
                counts["unreviewed"] += 1
                continue
            if doc.get("original") != current:
                stale.append(lid)
                continue
            if doc.get("status") == "corrected" and isinstance(doc.get("text"), str):
                corr[(pg, bi, li)] = doc["text"]
                counts["corrected"] += 1
            elif doc.get("status") == "confirmed":
                counts["confirmed"] += 1
            else:
                counts["unreviewed"] += 1
    return corr, counts, stale


# ------------------------------------------------------------------ shared scan

def pool_of(db, other):
    doc = db["release"].get(other)
    if doc is None:
        return "unsorted"
    pool = doc.get("pool")
    return pool if pool in POOLS else "unknown"


def shared_scan(src, db, pid, indices, public_ids, accepted):
    """Every other piece (and non-piece 'other lines' item) on a page the published versions sit on.
    status: ok | accepted | needs-accept | stop"""
    out = []
    direct = src.pages_of(pid, indices)
    mates = src.spread_mates(direct)  # the spread image of a published page shows the facing page too
    pages = set(direct) | set(mates)
    via = lambda pg: " (facing page of the spread image)" if pg in mates else ""
    for q in src.j["pieces"]:
        if q["id"] == pid:
            continue
        on = sorted({pg for v in q["V"] for pg, _ in v["P"] if pg in pages})
        for pg in on:
            if q["id"] in public_ids:
                out.append(dict(page=pg, id=q["id"], status="ok", reason="already public or posted in this run" + via(pg)))
                continue
            pool = pool_of(db, q["id"])
            if pool == "series":
                if q["id"] in accepted:
                    out.append(dict(page=pg, id=q["id"], status="accepted", reason="Series, not yet public; accepted with --accept-shared-scan" + via(pg)))
                else:
                    out.append(dict(page=pg, id=q["id"], status="needs-accept", reason="Series but not public yet; pass --accept-shared-scan " + q["id"] + via(pg)))
            else:
                out.append(dict(page=pg, id=q["id"], status="stop", reason=f"pool is {pool}: its writing would be visible in the scan" + via(pg)))
    for it in src.review["items"]:
        if it["id"] in src.pieces:
            continue
        for v in it["versions"]:
            if v["page"] in pages:
                if it["id"] in accepted:
                    out.append(dict(page=v["page"], id=it["id"], status="accepted", reason="other lines on the page; accepted with --accept-shared-scan" + via(v["page"])))
                else:
                    out.append(dict(page=v["page"], id=it["id"], status="needs-accept", reason="other lines (not a poem) are visible in the scan; pass --accept-shared-scan " + it["id"] + via(v["page"])))
    return out


# ------------------------------------------------------------------ fonts, audit, output checks

FONT_RE = re.compile(r"@font-face\s*\{[^}]*?font-family\s*:\s*[\"']?([^\"';}]+)[\"']?[^}]*?src\s*:\s*url\(\s*data:font/([a-z0-9]+);base64,([A-Za-z0-9+/=]+)", re.I | re.S)


def find_embedded_fonts(html):
    return [dict(family=m.group(1).strip(), kind=m.group(2), bytes=len(m.group(3)) * 3 // 4) for m in FONT_RE.finditer(html)]


def strip_data_uris(html):
    return re.sub(r"data:[a-z0-9/+.-]+;base64,[A-Za-z0-9+/=]+", "data:...", html, flags=re.I)


def audit_strings(out_dir):
    """Reader-visible strings the build would publish, as (kind, value) rows. It only lists; the author decides."""
    out = Path(out_dir)
    rows = []
    html_path = out / "index.html"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    plain = strip_data_uris(html)
    m = re.search(r"<title>(.*?)</title>", plain, re.S)
    rows.append(("title", m.group(1).strip() if m else "(none)"))
    for v in sorted(set(re.findall(r"aria-label=\"([^\"]*)\"", plain))):
        rows.append(("aria-label", v))
    for v in sorted(set(re.findall(r"\balt=\"([^\"]*)\"", plain))):
        rows.append(("alt", v))
    for f in find_embedded_fonts(html):
        rows.append(("font embedded", f"{f['family']} ({f['kind']}, about {f['bytes']} bytes, downloadable)"))
    seen = set()
    for m in re.finditer(r"etceter4", plain, re.I):
        ctx = re.sub(r"\s+", " ", plain[max(0, m.start() - 30):m.end() + 30]).strip()
        if ctx not in seen:
            seen.add(ctx)
            rows.append(("name mention", ctx))
    jpath = out / "data" / "j.json"
    if jpath.exists():
        j = json.loads(jpath.read_text())
        rows.append(("prov keys", ", ".join(sorted(j.get("prov", {}))) or "(none)"))
        notes = sum(len(p.get("u") or []) for p in j["pages"])
        blk = sum(1 for p in j["pages"] for b in p["B"] if "u" in b)
        rows.append(("block notes", f"page reading notes: {notes}; blocks carrying a note flag: {blk}"))
        prov = j.get("prov", {})
        rows.append(("info panel (from prov)", "Machine transcription (%s), %s by the author. Spelling and line breaks kept." % (prov.get("tdate", ""), "checked" if prov.get("verified") else "not yet checked")))
        if not ({"repo", "commit", "path"} & set(prov)):
            rows.append(("info panel (from prov)", "Scans: line renders with an empty link, empty commit and empty path (source repository keys removed)"))
    return rows


def _text_files(out):
    for p in sorted(Path(out).rglob("*")):
        if p.is_file() and p.suffix.lower() in (".json", ".html", ".txt", "") :
            yield p


def leak_check(src, out, published, texts_ok):
    """Nothing written on an unpublished block, and no page reading note, may be in the output.
    `published` is the set of (page, block) published; `texts_ok` the strings that may appear.
    Two tests, both returning the offending strings:
      structure: in the output data, every block outside `published` has only empty lines, and
                 every non-empty line anywhere is a published reading or correction; no page notes;
      text:      no multi-word line of an unpublished block (or page note) appears as a substring of any
                 output text file (single words are skipped: they occur in the page code by chance)."""
    out = Path(out)
    bad = set()
    jpath = out / "data" / "j.json"
    if jpath.exists():
        for p in json.loads(jpath.read_text())["pages"]:
            bad.update(p.get("u") or [])
            for bi, b in enumerate(p["B"]):
                for s in b["L"]:
                    if s and (s not in texts_ok or (p["id"], bi) not in published):
                        bad.add(s)
    secrets = set()
    for p in src.j["pages"]:
        for bi, b in enumerate(p["B"]):
            if (p["id"], bi) not in published:
                secrets.update(b["L"])
        secrets.update(p.get("u") or [])
    secrets = {s for s in secrets if len(s) >= 12 and re.search(r"\s", s) and s != PLACEHOLDER} - texts_ok
    blob = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in _text_files(out))
    bad.update(s for s in secrets if s in blob)
    return sorted(bad)


def check_output(src, out, effective, published, texts_ok, pieces_expected):
    """-> [(name, ok, detail)] checks run on the build output."""
    out = Path(out)
    res = []
    html = (out / "index.html").read_text(encoding="utf-8")
    res.append(("index.html has <meta name=\"robots\" content=\"noindex\"> (or a stricter robots tag that includes noindex)", build_public.has_noindex(html), ""))
    named = []
    for p in _text_files(out):
        if p.name != "index.html":  # index.html names the embedded font; that is the --accept-embedded-font stop
            if OLD_NAME_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                named.append(p.relative_to(out).as_posix())
    res.append(("no output text file other than index.html names the other project", not named, ", ".join(named)))
    hdr = out / "_headers"
    h = hdr.read_text() if hdr.exists() else ""
    res.append(("_headers sets X-Robots-Tag: noindex for /*", bool(re.search(r"^/\*\s*\n\s+X-Robots-Tag:\s*noindex\s*$", h, re.M)), ""))
    j = json.loads((out / "data" / "j.json").read_text())
    res.append(("data/j.json has no prov.repo, prov.commit, prov.path", not ({"repo", "commit", "path"} & set(j.get("prov", {}))), ""))
    res.append(("data/j.json lists exactly the expected pieces", [p["id"] for p in j["pieces"]] == pieces_expected, ""))
    missing = [f"img/{s}/{p['id']}.jpg" for p in j["pages"] for s in ("p", "i", "m") if not (out / "img" / s / f"{p['id']}.jpg").is_file()]
    missing += [f"img/a/{k}0.jpg" for k in ("t", "k") if j["pages"] and not (out / "img" / "a" / f"{k}0.jpg").is_file()]
    res.append(("every image the data asks for is in the output", not missing, ", ".join(missing[:5])))
    leaks = leak_check(src, out, published, texts_ok)
    res.append(("no line of an unpublished block appears in the output", not leaks, f"{len(leaks)} string(s) found" if leaks else ""))
    return res


def tree_listing(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): p.stat().st_size for p in sorted(root.rglob("*")) if p.is_file()}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_hashes(root):
    root = Path(root)
    return {p.relative_to(root).as_posix(): (p.stat().st_size, sha256_file(p)) for p in sorted(root.rglob("*")) if p.is_file()} if root.is_dir() else {}


# ------------------------------------------------------------------ public repository

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip() if check else r


def remote_is_public_repo(url):
    return bool(re.search(r"github\.com[:/]" + re.escape(PUBLIC_REPO_NAME) + r"(\.git)?/?$", url.strip(), re.I))


def check_public_repo(path, branch):
    """-> [(name, ok, detail)]. Writes nothing in the repository (no fetch; ls-remote only)."""
    res = []
    p = Path(path)
    if not (p / ".git").exists():
        return [("public repo is a git checkout", False, str(path))]
    url = git(p, "config", "--get", "remote.origin.url", check=False).stdout.strip()
    res.append((f"remote origin is {PUBLIC_REPO_NAME}", remote_is_public_repo(url), url or "no origin"))
    cur = git(p, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    res.append(("on branch main", cur == "main", f"on {cur!r}"))
    dirty = git(p, "--no-optional-locks", "status", "--porcelain", check=False).stdout.strip()  # does not refresh .git/index
    res.append(("working tree clean", not dirty, f"{len(dirty.splitlines())} changed or untracked path(s)" if dirty else ""))
    head = git(p, "rev-parse", "HEAD", check=False).stdout.strip()
    ls = git(p, "ls-remote", "origin", "refs/heads/main", check=False)
    remote = ls.stdout.split()[0] if ls.returncode == 0 and ls.stdout.split() else ""
    res.append(("main is fetched (local HEAD equals origin/main)", bool(remote) and remote == head, "cannot reach origin" if not remote else f"origin/main is {remote[:7]}, HEAD is {head[:7]}"))
    local_b = git(p, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    remote_b = git(p, "ls-remote", "--heads", "origin", f"refs/heads/{branch}", check=False)
    res.append((f"branch {branch} does not exist yet", local_b.returncode != 0 and not remote_b.stdout.strip(), "already exists"))
    return res


def fill_public_repo(repo, build_dir, branch, message):
    """Branch from main, replace site/ with exactly the build output, commit. Returns commit sha."""
    repo = Path(repo)
    git(repo, "checkout", "-b", branch)
    site = repo / "site"
    if site.exists():
        shutil.rmtree(site)
    shutil.copytree(build_dir, site)
    git(repo, "add", "-A", "site")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


# ------------------------------------------------------------------ pull request text

def render_pr_body(ctx):
    L = []
    L.append("## What changed")
    L.append(f"- Piece(s): {', '.join(ctx['pids'])}")
    for pid in ctx["pids"]:
        L.append(f"- {pid}: {ctx['versions'][pid]['how']}; version(s) published: {len(ctx['versions'][pid]['indices'])} of {ctx['versions'][pid]['total']}")
    L.append(f"- Pages in the public site: {len(ctx['pages'])} ({', '.join(ctx['pages'])})")
    d = ctx["diff"]
    L.append(f"- Files: {len(d['added'])} added, {len(d['changed'])} changed, {len(d['removed'])} removed; {d['bytes']} bytes in the new site/")
    for kind in ("added", "changed", "removed"):
        if d[kind]:
            L.append(f"  - {kind}: " + ", ".join(sorted(d[kind])[:40]) + (" ..." if len(d[kind]) > 40 else ""))
    L.append("")
    L.append("## How verified")
    for kind, pid, name, ok, detail, forced in ctx["results"]:
        word = "PASS" if ok else ("FAIL (forced)" if forced else "FAIL")
        L.append(f"- {word} {name} [{pid}]" + (f": {detail}" if detail else ""))
    for name, ok, detail in ctx["checks"]:
        L.append(f"- {'PASS' if ok else 'FAIL'} {name}" + (f": {detail}" if detail else ""))
    for pid, c in ctx["counts"].items():
        L.append(f"- {pid} lines: {c['confirmed']} confirmed, {c['corrected']} corrected (author text published), {c['unreviewed']} without review")
    L.append(f"- sha256 of data/j.json: `{ctx['sha']}`")
    L.append("")
    L.append("## Not verified")
    L.append("- Rendering on a real phone or other device")
    L.append("- A Cloudflare Pages preview deploy of this branch")
    L.append("- Author sign-off on the shared scans listed here: " + (", ".join(f"{f['id']} on {f['page']} ({f['status']})" for f in ctx["shared"]) or "none found"))
    L.append("- Author sign-off on the embedded font (font file and its name become downloadable): " + (", ".join(ctx["fonts"]) or "none embedded"))
    for w in ctx["warnings"]:
        L.append(f"- {w}")
    L.append("- Reader-visible strings (list only; the author decides):")
    for kind, value in ctx["audit"]:
        L.append(f"  - {kind}: {value[:140]}")
    L.append("")
    L.append("Merging is the author's decision. To undo a post: `git revert` the merge commit in this repository.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main flow

def parse_args(argv):
    ap = argparse.ArgumentParser(description="Gate, build and prepare a pull request for posting a poem.")
    ap.add_argument("pieces", nargs="+", metavar="PIECE_ID")
    ap.add_argument("--db", required=True, help="studio database export directory (COLLECTION/DOCID.json)")
    ap.add_argument("--public-repo", help="clone of 4444J99/versforms (required unless --dry-run)")
    ap.add_argument("--include-versions", action="store_true", help="publish the whole version stack (needs the author's approval)")
    ap.add_argument("--force", action="store_true", help="override the three gates only")
    ap.add_argument("--accept-shared-scan", action="append", default=[], metavar="IDS", help="ids of Series pieces / other-line items whose writing may show in a shared scan")
    ap.add_argument("--accept-embedded-font", action="store_true", help="accept that index.html embeds a downloadable font whose name becomes public")
    ap.add_argument("--dry-run", action="store_true", help="run every gate and hard stop, build into scratch, write nothing in the public repo")
    ap.add_argument("--no-pr", action="store_true", help="commit the branch in the public clone but do not push or open a PR")
    ap.add_argument("--workdir", help="scratch directory for the build (default: a new post-poem-* directory next to the private repository)")
    ap.add_argument("--source", default=str(ROOT), help="private repository root (default: this repository)")
    return ap.parse_args(argv)


def run(a):
    root = Path(a.source)
    pids = list(dict.fromkeys(a.pieces))
    accepted = {x for chunk in a.accept_shared_scan for x in re.split(r"[,\s]+", chunk) if x}
    results = []  # (kind, pid, name, ok, detail, forced)

    def record(kind, pid, name, ok, detail=""):
        results.append((kind, pid, name, ok, detail, False))
        say(f"{'PASS' if ok else 'FAIL'}  {kind:<4} {name} [{pid}]" + (f": {detail}" if detail else ""))

    try:
        src = Source(root)
        db = load_db(a.db)
    except Stop as e:
        say(f"FAIL  stop cannot load inputs: {e}")
        return EXIT_STOP
    unknown = [p for p in pids if p not in src.pieces]
    for p in unknown:
        record("stop", p, "piece id exists in site/data/j.json", False, "unknown piece id")
    if unknown:
        return EXIT_STOP
    effective = list(dict.fromkeys(src.public + pids))
    all_versions = set(src.all_versions) | (set(pids) if a.include_versions else set())

    say(f"Posting {', '.join(pids)} (dry run)" if a.dry_run else f"Posting {', '.join(pids)}")
    # --- gates (requested pieces only)
    for pid in pids:
        record("gate", pid, "(a) in Series", *gate_series(db, pid))
        own = pool_of(db, pid)
        if own in ("reserve", "archive"):
            # --force overrides the gates only: a Reserve or Archive piece never goes online in any form
            record("stop", pid, "requested piece is not in Reserve or Archive", False, f"pool is {own}; --force does not override this")
        record("gate", pid, "(b) every line confirmed or corrected", *gate_verified(src, db, pid))
        record("gate", pid, "(c) in a filed or registered batch", *gate_filed(db, pid))

    # --- versions, corrections, stale transcript, shared scan
    versions, corrections, counts, warnings, shared_all = {}, {}, {}, [], []
    select = {}
    try:
        for pid in effective:
            if pid in all_versions:
                idx, how, notes = list(range(len(src.pieces[pid]["V"]))), "whole stack", []
            else:
                idx, how, notes = select_versions(src, db, pid, False)
            select[pid] = idx
            versions[pid] = dict(indices=idx, how=how, total=len(src.pieces[pid]["V"]))
            if pid in pids:
                warnings.extend(f"{pid}: {n}" for n in notes)
                n_v = len(src.pieces[pid]["V"])
                if not a.include_versions and how.startswith("top") and idx != [n_v - 1]:
                    warnings.append(f"{pid}: the top of the stack (V[{idx[0]}]) is not the last entry of V (V[{n_v - 1}]); the engine's own order labels the last entry 'newest'. Publishing the top; check this is the version the author wants")
    except Stop as e:
        say(f"FAIL  stop {e}")
        return EXIT_STOP
    for pid in src.public:
        if pid not in pids:
            pool = pool_of(db, pid)
            if pool != "series":
                warnings.append(f"{pid} is already in release/public.json and is rebuilt into this site, but its release pool is now {pool}. Its pool, gates and shared scans are not rechecked here; decide whether it should stay public")
    for pid in effective:
        v = versions[pid]
        say(f"versions {pid}: publishing {len(v['indices'])} of {v['total']} ({v['how']})")
    if a.include_versions:
        say("NOTE  --include-versions publishes the whole version stack of: " + ", ".join(pids) + ". This needs the author's approval.")
    for pid in effective:
        c, n, stale = load_corrections(src, db, pid, select[pid])
        corrections.update(c)
        counts[pid] = n
        if stale:
            record("stop", pid, "(ii) no stale transcript", False, f"review 'original' differs from the machine reading on {len(stale)} line(s): " + ", ".join(stale[:20]))
        elif pid in pids:
            record("stop", pid, "(ii) no stale transcript", True)
        if n["unreviewed"] and pid in pids:
            warnings.append(f"{pid}: {n['unreviewed']} published line(s) have no review; the machine reading is published for them")
    public_ids = set(effective)
    for pid in pids:
        finds = shared_scan(src, db, pid, select[pid], public_ids, accepted)
        shared_all.extend(finds)
        bad = [f for f in finds if f["status"] in ("stop", "needs-accept")]
        detail = f"{len(finds)} co-resident piece(s) or item(s) on {len(src.pages_of(pid, select[pid]))} page(s)"
        if bad:
            detail += "; " + "; ".join(f"{f['id']} on {f['page']}: {f['reason']}" for f in bad)
        record("stop", pid, "(i) shared scan", not bad, detail)
        for f in finds:
            if f["status"] == "accepted":
                say(f"  accepted shared scan: {f['id']} on {f['page']}")
        extra = sorted(accepted - {f["id"] for f in finds})
        if extra:
            warnings.append(f"--accept-shared-scan named ids that share no scan with {pid}: {', '.join(extra)}")
        sib = {pg for pg in src.pages_of(pid, select[pid]) for q in [src.pieces[pid]]
               for vi, v in enumerate(q["V"]) if vi not in select[pid] for p2, _ in v["P"] if p2 == pg}
        if sib:
            warnings.append(f"{pid}: the scan of {', '.join(sorted(sib))} also shows writing of its unpublished version(s)")
    for vdoc in db["versions"].values():
        if vdoc.get("pieceId") in pids:
            warnings.append(f"{vdoc.get('pieceId')}: the studio holds a new-version photo for this piece that is not in site/data/j.json yet")

    # --- public repository
    branch = "post/" + "-".join(pids)
    pub_checks = []
    if a.public_repo:
        pub_checks = check_public_repo(a.public_repo, branch)
        for name, ok, detail in pub_checks:
            record("stop", ",".join(pids), name, ok, detail)
    elif a.dry_run:
        say("SKIP  stop public repository preconditions (no --public-repo given)")
    else:
        say("FAIL  stop --public-repo is required unless --dry-run")
        return EXIT_USAGE

    # --- embedded font
    html_src = (src.site / "index.html").read_text(encoding="utf-8")
    fonts = find_embedded_fonts(html_src)
    font_names = [f"{f['family']} ({f['bytes']} bytes)" for f in fonts]
    if fonts:
        why = "index.html embeds " + ", ".join(font_names) + ": the font file becomes downloadable from the public site and its name becomes public"
        if a.dry_run:
            say(f"WARN  stop embedded font: {why}. A real run needs --accept-embedded-font.")
        else:
            record("stop", ",".join(pids), "embedded font accepted (--accept-embedded-font)", a.accept_embedded_font, "" if a.accept_embedded_font else why)

    stops = [r for r in results if r[0] == "stop" and not r[3]]
    gates = [r for r in results if r[0] == "gate" and not r[3]]
    if stops:
        say(f"\nREFUSED: {len(stops)} hard stop(s). --force does not override these.")
        return EXIT_STOP
    if gates and not a.force:
        say(f"\nREFUSED: {len(gates)} gate(s) failed. Fix them in the studio, or use --force to override the gates only.")
        return EXIT_GATE
    if gates:
        results[:] = [(k, p, n, ok, d, (not ok and k == "gate")) for k, p, n, ok, d, _ in results]
        say(f"\nFORCED past {len(gates)} failed gate(s).")

    # --- build
    # default scratch: a new directory beside the private repository, never the system temp directory
    workdir = Path(a.workdir) if a.workdir else Path(tempfile.mkdtemp(prefix="post-poem-", dir=str(root.resolve().parent)))
    workdir.mkdir(parents=True, exist_ok=True)
    out = workdir / "build"
    res = build_public.build(out, effective, site=src.site, select=select, corrections=corrections, strip_prov=True)
    published = set(res["published"])
    texts_ok = {s for (pg, bi) in published for s in src.jpages[pg]["B"][bi]["L"]} | set(corrections.values())
    checks = check_output(src, out, effective, published, texts_ok, effective)
    for name, ok, detail in checks:
        say(f"{'PASS' if ok else 'FAIL'}  check {name}" + (f": {detail}" if detail else ""))
    if not all(ok for _, ok, _ in checks):
        say("\nREFUSED: the build output failed its own checks.")
        return EXIT_STOP
    for pg, ids in sorted(res["shared"].items()):
        say(f"  note: {pg} also carries {sorted(ids)} — visible in the scan, text withheld")
    listing = tree_listing(out)
    sha = sha256_file(out / "data" / "j.json")
    say(f"\nbuild: {len(listing)} files, {sum(listing.values())} bytes, {len(res['pages'])} page(s), {res['applied']} correction(s) applied")
    say(f"data/j.json sha256 {sha}")
    audit = audit_strings(out)
    title = next((v for k, v in audit if k == "title"), "")
    say(f"WARNING  visible title is {title!r}; the author's decision on the title is pending and this script does not change it.")
    say("reader-visible strings (list only):")
    for kind, value in audit:
        say(f"  {kind}: {value[:140]}")
    for kind, value in audit:
        if kind == "info panel (from prov)":
            warnings.append(f"info panel text produced from prov: {value}")
    for w in warnings:
        say(f"WARNING  {w}")

    if a.dry_run:
        say("\nfile list:")
        for rel, size in listing.items():
            say(f"  {size:>9}  {rel}")
        say("\nDRY RUN: nothing written in the public repository, nothing pushed, release/public.json unchanged.")
        say("would write release/public.json pieces: " + ", ".join(effective))
        return EXIT_OK

    # --- public repository: branch, replace site/, commit
    before = tree_hashes(Path(a.public_repo) / "site")
    after = tree_hashes(out)
    diff = dict(added=[k for k in after if k not in before], changed=[k for k in after if k in before and after[k] != before[k]],
                removed=[k for k in before if k not in after], bytes=sum(s for s, _ in after.values()))
    try:
        sha_commit = fill_public_repo(a.public_repo, out, branch, "Post " + ", ".join(pids))
    except RuntimeError as e:
        say(f"ERROR  {e}")
        return EXIT_PARTIAL
    say(f"committed {sha_commit[:7]} on branch {branch} in {a.public_repo}")
    ctx = dict(pids=pids, versions=versions, pages=res["pages"], diff=diff, results=results, checks=checks + pub_checks,
               counts={p: counts[p] for p in pids}, sha=sha, shared=shared_all, fonts=font_names, warnings=warnings, audit=audit)
    body = render_pr_body(ctx)
    (workdir / "pr-body.md").write_text(body)
    if not a.no_pr:
        try:
            git(a.public_repo, "push", "-u", "origin", branch)
            r = subprocess.run(["gh", "pr", "create", "--repo", PUBLIC_REPO_NAME, "--base", "main", "--head", branch,
                                "--title", "Post " + ", ".join(pids), "--body-file", str(workdir / "pr-body.md")],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"gh pr create failed: {r.stderr.strip()}")
            say(f"pull request: {r.stdout.strip()}")
        except (RuntimeError, OSError) as e:
            say(f"ERROR  {e}\nThe branch is committed locally in {a.public_repo}; private release/public.json is NOT updated. PR text: {workdir / 'pr-body.md'}")
            return EXIT_PARTIAL
    else:
        say(f"--no-pr: branch not pushed. PR text is in {workdir / 'pr-body.md'}")

    # --- private release list (not committed)
    update_release_list(src, pids, all_versions)
    return EXIT_OK


def update_release_list(src, pids, all_versions):
    path = src.release_path
    old = path.read_text() if path.exists() else ""
    cur = json.loads(old) if old.strip() else {"pieces": []}
    cur["pieces"] = list(dict.fromkeys(list(cur.get("pieces", [])) + pids))
    if all_versions:
        cur["all_versions"] = [p for p in cur["pieces"] if p in all_versions]
    new = json.dumps(cur, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new)
    say(f"updated {path} (not committed):")
    r = subprocess.run(["git", "-C", str(path.parent), "diff", "--", str(path)], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        say(r.stdout.rstrip())
    else:
        say("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "release/public.json", "release/public.json")).rstrip())


def main(argv=None):
    a = parse_args(argv)
    try:
        return run(a)
    except Stop as e:
        say(f"FAIL  stop {e}")
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
