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
         the old project name found anywhere in the output (text, decoded fonts), an embedded font
         that does not parse, an embedded font that cannot be decoded here (no font venv) without
         --accept-embedded-font, output checks
    64 usage error
    1  an operation failed part-way (git, gh); the message says what state was left

stdlib and Pillow only. Poem text is never printed, logged, or put in a commit or PR body.
"""
import argparse, base64, difflib, hashlib, json, os, re, shutil, subprocess, sys, tempfile, unicodedata, urllib.parse
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import build_public  # noqa: E402

PUBLIC_REPO_NAME = "4444J99/versforms"
COLLECTIONS = ("reviews", "decisions", "versions", "release", "batches", "rconfig")
POOLS = ("series", "reserve", "archive")
PLACEHOLDER = "[[quoted passage:]]"
OLD_NAME_RE = build_public.OLD_NAME_RE  # the author's music; no vers.forms artifact may name it
DEFAULT_SCRATCH = ".post-poem-work"
WORKDIR_MARK = ".post-poem-workdir"
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
        try:
            rel = build_public.load_release(self.release_path)
        except (OSError, ValueError) as e:
            raise Stop(f"cannot read release/public.json under {self.root}: {e}")
        pub, allv = (rel.get("pieces", []), rel.get("all_versions", [])) if isinstance(rel, dict) else (None, None)
        if not (isinstance(pub, list) and isinstance(allv, list) and all(isinstance(x, str) for x in pub + allv)):
            raise Stop("release/public.json must be an object whose 'pieces' (and optional 'all_versions') are lists of piece id strings")
        self.public = list(dict.fromkeys(pub))
        self.all_versions = list(dict.fromkeys(allv))
        unknown = [x for x in self.public + self.all_versions if x not in self.pieces]
        if unknown:
            raise Stop(f"release/public.json names piece id(s) that are not in site/data/j.json: {', '.join(unknown[:8])}")

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

    def scan_twins(self):
        """{page id: {other page ids whose p, i or m scan file is byte-identical}}. Cached. Files are compared by
        size first, so only files that could be equal are hashed."""
        if getattr(self, "_twins", None) is not None:
            return self._twins
        by_size = {}
        for q in self.j["pages"]:
            for sub in ("p", "i", "m"):
                f = self.site / "img" / sub / f"{q['id']}.jpg"
                try:
                    by_size.setdefault((sub, f.stat().st_size), []).append((q["id"], f))
                except OSError:
                    continue
        twins = {}
        for group in by_size.values():
            if len(group) < 2:
                continue
            by_hash = {}
            for pid_, f in group:
                by_hash.setdefault(hashlib.sha256(f.read_bytes()).hexdigest(), set()).add(pid_)
            for same in by_hash.values():
                for pid_ in same:
                    twins.setdefault(pid_, set()).update(same - {pid_})
        self._twins = twins
        return twins

    def spread_mates(self, pages):
        """Pages whose writing is visible in the scan files the build copies for `pages`.

        * A page with sp.f: the build copies img/s/{sp.f}.jpg, the whole two-page spread, so the other page of the
          spread (the same sp.k or sp.f, or the page the file is named after) is in the downloaded image. If no such
          page can be identified the facing page is unknown, and that is a hard stop (Stop), not "no mates".
        * A page whose own scan IS the whole spread (sp.s == 'whole spread', or no crop box): the page's p/i/m files show
          both halves, so every other page with the same sp.k is a mate.
        * Belt and braces: any page whose p, i or m scan file is byte-identical to one of these pages' files."""
        pages = set(pages)
        mates = set()
        for pg in pages:
            sp = self.jpages[pg].get("sp") or {}
            f, k = sp.get("f"), sp.get("k")
            if f:
                found = {q["id"] for q in self.j["pages"]
                         if q["id"] != pg and ((k and (q.get("sp") or {}).get("k") == k) or (q.get("sp") or {}).get("f") == f or q["id"] == f)}
                if not found:
                    raise Stop(f"page {pg}: its spread image ({f}.jpg) is copied into the public site, but no facing page can be identified "
                               f"(no other page shares sp.k {k!r} or sp.f {f!r}, and no page record is named {f!r}), so what is written on the other half cannot be checked")
                mates |= found
            elif sp.get("s") == "whole spread" or sp.get("cb") is None:
                if k:
                    mates |= {q["id"] for q in self.j["pages"] if q["id"] != pg and (q.get("sp") or {}).get("k") == k}
            mates |= self.scan_twins().get(pg, set())
        return sorted(mates - pages)

    def published_blocks(self, pid, indices):
        return sorted({(pg, b) for i in indices for pg, bl in self.pieces[pid]["V"][i]["P"] for b in bl})


def find_db_root(path):
    """The export directory: --db itself when it holds collection folders, else the ONE exports/* directory that does.
    Zero or several candidates are a hard stop: guessing would load nothing (or the wrong export), and every piece
    would then read as 'unsorted', which is only a gate that --force overrides."""
    base = Path(path)
    if not base.is_dir():
        raise Stop(f"--db {path} is not a directory")
    if any((base / c).is_dir() for c in COLLECTIONS):
        return base
    nested = sorted(p for p in base.glob("exports/*") if any((p / c).is_dir() for c in COLLECTIONS))
    if len(nested) == 1:
        return nested[0]
    if not nested:
        raise Stop(f"--db {path} holds no studio export: none of the folders {', '.join(COLLECTIONS)} here or in exports/*")
    raise Stop(f"--db {path} holds {len(nested)} exports ({', '.join(p.name for p in nested)}); name the one to use with --db")


RELEASE_DOC_NAME_RE = re.compile(r"p[0-9]+\.json")  # exactly: lowercase p, ASCII digits, .json


def _fold(name):
    """A name as a human would read it: compatibility-normalised, format and control characters dropped, outer spaces
    and dots stripped, lower case. Used only to recognise look-alikes, never to accept one."""
    kept = "".join(ch for ch in unicodedata.normalize("NFKC", name) if unicodedata.category(ch) not in ("Cf", "Cc"))
    return kept.strip().strip(".").strip().lower()


def check_export_names(root, piece_ids=None):
    """Every release document is named exactly p<digits>.json AND that id is a piece that exists, and no folder only
    RESEMBLES a collection folder. A document whose name merely looks right (P001.json, p001.JSON, 'p001 .json',
    fullwidth digits), has the right shape but names no piece (p0001.json, p1.json, a name padded with zeros, the id of a
    piece that no longer exists) or is a stray file would otherwise be ignored: its piece would then read as 'unsorted'
    (a gate that --force overrides) while a Reserve document sits next to it. A hard stop, naming the entry; --force
    does not override it. `piece_ids` is the set of ids in site/data/j.json; a run always passes it. The one tolerated
    stranger is a regular file named exactly .DS_Store (Finder creates it)."""
    for entry in sorted(os.listdir(root)):
        if entry not in COLLECTIONS and _fold(entry) in COLLECTIONS:
            raise Stop(f"{root}/{entry!r} looks like the collection {_fold(entry)!r} but is not named exactly that, so its documents would be ignored. Rename or remove it")
    folder = Path(root) / "release"
    if folder.is_dir():
        for entry in sorted(os.listdir(folder)):
            if entry == ".DS_Store" and (folder / entry).is_file() and not (folder / entry).is_symlink():
                continue
            if not RELEASE_DOC_NAME_RE.fullmatch(entry):
                raise Stop(f"release/{entry!r} is not a release document name: they are exactly p<digits>.json (lowercase, ASCII digits, no spaces). "
                           "A file that only resembles one would be ignored and its piece would read as unsorted, even if it says Reserve. Rename or remove it")
            if (folder / entry).is_symlink() or not (folder / entry).is_file():
                raise Stop(f"release/{entry!r} is not a regular file (a directory or a link); a release document must be a plain file")
            if piece_ids is not None and entry[:-len(".json")] not in piece_ids:
                raise Stop(f"release/{entry[:80]!r} names no piece: {entry[:-len('.json')][:40]!r} is not a piece id in site/data/j.json (zero padding, extra digits and the id of a piece that no longer exists all end here). "
                           "A release document that names no piece would be ignored while a Reserve document sits in it. Rename or remove it")


def load_db_with_root(path, piece_ids=None):
    """-> (export directory, {collection: {doc id: doc}}) from EXPORT_DIR/COLLECTION/DOCID.json.
    A document that is not a JSON object, a release entry or a collection folder whose name only resembles the
    right one, a release document that names no piece (when `piece_ids` is given, as a run always does), and an
    export with no release documents at all, are hard stops."""
    root = find_db_root(path)
    check_export_names(root, piece_ids)
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
            if not isinstance(doc, dict):
                raise Stop(f"{f}: not a JSON object ({type(doc).__name__}); a studio document is always an object, so this export is damaged")
            db[c][f.stem] = doc
    if not db["release"]:
        raise Stop(f"the export {root} has no release documents, so no piece has a pool and every piece would read as unsorted; this is the wrong folder or a damaged export")
    return root, db


def load_db(path):
    return load_db_with_root(path)[1]


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
    """Passes when ANY batch listing the piece is filed or registered (a piece may sit in a draft batch and
    also in a later filed one)."""
    found, malformed = [], 0
    for bid, b in sorted(db["batches"].items()):
        items = b.get("items")
        if not isinstance(items, list):
            malformed += 1  # a string would make `pid in items` a substring match ('p0010 p0099' contains 'p001')
            continue
        if pid in items:
            found.append((bid, b.get("status")))
    note = f" ({malformed} batch document(s) whose items are not a list were ignored)" if malformed else ""
    if not found:
        return False, "not listed in any batch" + note
    for bid, status in found:
        if isinstance(status, str) and status in ("filed", "registered"):
            return True, f"batch {bid} is {status!r}"
    return False, "; ".join(f"batch {bid} is {status!r}" for bid, status in found) + note


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
    counts = {"confirmed": 0, "corrected": 0, "unreviewed": 0, "withheld": 0}
    for pg, bi in src.published_blocks(pid, indices):
        if src.jpages[pg]["B"][bi].get("t") == 4:
            counts["withheld"] += len(src.jpages[pg]["B"][bi]["L"])  # quotation block: its lines stay withheld, reviews on them are not used
            continue
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


def unpublished_corrections(src, db, pid, indices):
    """How many lines carrying an author correction ('corrected' review with text) sit on versions of the
    piece that are NOT published (blocks that are also part of a published version do not count)."""
    pub = set(src.published_blocks(pid, indices))
    seen = set()
    for i, v in enumerate(src.pieces[pid]["V"]):
        if i in indices:
            continue
        for pg, blocks in v["P"]:
            for b in blocks:
                if (pg, b) in pub:
                    continue
                for li in range(len(src.jpages[pg]["B"][b]["L"])):
                    doc = db["reviews"].get(f"{pg}-{b}-{li}")
                    if doc and doc.get("status") == "corrected" and isinstance(doc.get("text"), str):
                        seen.add(f"{pg}-{b}-{li}")
    return len(seen)


# ------------------------------------------------------------------ shared scan

def pool_of(db, other):
    """'series' | 'reserve' | 'archive' | 'unsorted' (no release document) | 'unknown' (any other value:
    'Reserve', ' reserve', a list, a number, null...). Only the studio's exact values count; a value that merely
    looks like Reserve is never read as 'not Reserve'."""
    doc = db["release"].get(other)
    if doc is None:
        return "unsorted"
    pool = doc.get("pool")
    return pool if isinstance(pool, str) and pool in POOLS else "unknown"


def pool_note(db, other):
    """What the release document says, for a message (never the document's other fields)."""
    doc = db["release"].get(other) or {}
    raw = doc.get("pool")
    like = raw.strip().lower() if isinstance(raw, str) else None
    return f"pool is {raw!r}" + (f", which reads like {like!r} but is not the exact value the studio writes" if like in POOLS and raw != like else "")


def shared_scan(src, db, pid, indices, public_ids, accepted):
    """Every other piece (and non-piece 'other lines' item) on a page the published versions sit on.
    status: ok | accepted | needs-accept | stop"""
    out = []
    direct = src.pages_of(pid, indices)
    mates = src.spread_mates(direct)  # the spread image of a published page shows the facing page too
    pages = set(direct) | set(mates)
    via = lambda pg: " (facing page of the spread image)" if pg in mates else ""
    seen = set()  # pages on which some piece or item was found
    for q in src.j["pieces"]:
        on = sorted({pg for v in q["V"] for pg, _ in v["P"] if pg in pages})
        if q["id"] == pid:
            # the piece's own writing on a facing page (another version) shows in the spread image
            for pg in on:
                if pg in mates:
                    seen.add(pg)
                    out.append(dict(page=pg, id=pid, status="ok", reason="another version of the same piece (facing page of the spread image)"))
            continue
        seen.update(on)
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
                seen.add(v["page"])
                if it["id"] in accepted:
                    out.append(dict(page=v["page"], id=it["id"], status="accepted", reason="other lines on the page; accepted with --accept-shared-scan" + via(v["page"])))
                else:
                    out.append(dict(page=v["page"], id=it["id"], status="needs-accept", reason="other lines (not a poem) are visible in the scan; pass --accept-shared-scan " + it["id"] + via(v["page"])))
    # a facing page with no piece and no review item cannot be shown to be blank: the author must name it
    for pg in sorted(set(mates) - seen):
        if pg in accepted:
            out.append(dict(page=pg, id=pg, status="accepted", reason="facing page of the spread image with no piece or review item; accepted with --accept-shared-scan"))
        else:
            out.append(dict(page=pg, id=pg, status="needs-accept", reason=f"facing page of the spread image; no piece or review item is known on it, so it cannot be shown to be blank; pass --accept-shared-scan {pg}"))
    return out


# ------------------------------------------------------------------ fonts, audit, output checks

FONT_RE = re.compile(r"@font-face\s*\{[^}]*?font-family\s*:\s*[\"']?([^\"';}]+)[\"']?[^}]*?src\s*:\s*url\(\s*data:font/([a-z0-9]+);base64,([A-Za-z0-9+/=]+)", re.I | re.S)


def find_embedded_fonts(html):
    return [dict(family=m.group(1).strip(), kind=m.group(2), bytes=len(m.group(3)) * 3 // 4) for m in FONT_RE.finditer(html)]


def strip_data_uris(html):
    return re.sub(r"data:[a-z0-9/+.-]+;base64,[A-Za-z0-9+/=]+", "data:...", html, flags=re.I)


def iter_data_uris(text):
    """(mime, decoded bytes) of every base64 data: URI in a text."""
    for m in build_public.DATA_URI_RE.finditer(text):
        try:
            yield m.group(1), base64.b64decode(m.group(2), validate=True)
        except ValueError:
            continue


OLD_FORMS = (OLD_NAME_RE.pattern.encode(), OLD_NAME_RE.pattern.encode("utf-16-be"), OLD_NAME_RE.pattern.encode("utf-16-le"))


def raw_has_old_name(data):
    """ASCII (which is also the Mac Roman spelling of these letters), UTF-16BE and UTF-16LE, any letter case."""
    low = bytes(data).lower()
    return any(f in low for f in OLD_FORMS)


def name_scan(out):
    """Search the whole output for the old project name, in any letter case.

    Every file: a text search (utf-8) and a raw byte search (ASCII / Mac Roman, UTF-16BE, UTF-16LE).
    Every base64 data: URI found in a text file is decoded; a font (by MIME type or magic bytes) goes
    through the font tool, which searches the decoded name table (all platforms, encodings and languages),
    the CFF strings, glyph names, the WOFF2 metadata and the raw bytes of every table; any other payload
    gets the raw byte search. A compressed WOFF2 stream cannot be searched as raw bytes, so for a font the
    decoded tables are the authority.
    -> dict(hits=[location, ...], fonts_checked=int, unchecked=[location, ...], undecodable=[location, ...], reason=str)
    unchecked: the font tool could not run at all (no venv python, fontTools or brotli missing): --accept-embedded-font
    may cover this. undecodable: the tool ran and the bytes did not parse as a font: always a hard stop.
    Locations are paths and field labels, never the matched text."""
    out = Path(out)
    hits, unchecked, undecodable, reason, checked = [], [], [], "", 0

    def check_payload(label, mime, raw):
        nonlocal reason, checked
        if raw_has_old_name(raw):
            hits.append(f"{label}: raw bytes")
        if build_public.is_font(mime, raw):
            try:
                doc = build_public.run_font_tool("check", raw)
            except build_public.FontDecodeError as e:
                undecodable.append(f"{label}: font does not parse")
                reason = reason or str(e)
                return
            except build_public.FontToolError as e:
                unchecked.append(f"{label}: font cannot be decoded here")
                reason = reason or str(e)
                return
            checked += 1
            hits.extend(f"{label}: font {h}" for h in doc["hits"])

    n_file = n_dir = 0
    for p in sorted(out.rglob("*")):
        if p.is_dir():
            n_dir += 1
            if OLD_NAME_RE.search(p.name):
                hits.append(f"output directory {n_dir}: its name")  # an empty directory has no file to carry the finding
            continue
        if not p.is_file():
            continue
        n_file += 1
        rel = p.relative_to(out).as_posix()
        data = p.read_bytes()
        if OLD_NAME_RE.search(rel):
            # file and directory names are public too. Say which file by position, never by the name, and
            # use that label for every other finding on the file so the log never repeats the name.
            hits.append(f"output file {n_file}: its path")
            rel = f"output file {n_file}"
        if OLD_NAME_RE.search(data.decode("utf-8", "ignore")):
            hits.append(f"{rel}: text")
        if raw_has_old_name(data):
            hits.append(f"{rel}: raw bytes")
        if data[:4] in build_public.FONT_MAGIC and data[:4] != b"\x00\x01\x00\x00":
            check_payload(rel, "font/" + rel.rsplit(".", 1)[-1], data)
        elif p.suffix.lower() in TEXT_SUFFIXES:
            for i, (mime, raw) in enumerate(iter_data_uris(data.decode("utf-8", "ignore"))):
                check_payload(f"{rel} data URI {i + 1} ({mime})", mime, raw)
    return dict(hits=sorted(set(hits)), fonts_checked=checked, unchecked=unchecked, undecodable=undecodable, reason=reason)


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
    try:
        names = set()
        for mime, raw in iter_data_uris(html):
            if build_public.is_font(mime, raw):
                d = build_public.run_font_tool("describe", raw)
                names.update(d["name_records"].values())
                names.update(d["cff_font_names"])
        for n in sorted(names):
            rows.append(("font file name", n))
    except build_public.FontToolError:
        rows.append(("font name records", "not listed: the font tool failed"))
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


TEXT_SUFFIXES = (".json", ".html", ".txt", ".css", ".js", ".svg", ".xml", ".md", "")


def _text_files(out):
    for p in sorted(Path(out).rglob("*")):
        if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
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
    # An unpublished line can be a fragment of a longer line that IS published (the same words occur in both).
    # Such a hit is not a leak: it is excused only where it lies inside an authorised published line, so the
    # occurrences inside those lines are removed before searching. Any occurrence outside them still counts.
    authorised = sorted((t for t in texts_ok if t), key=len, reverse=True)
    for sec in secrets:
        masked = blob
        for t in authorised:
            if len(t) > len(sec) and sec in t:
                for form in _json_forms(t):
                    masked = masked.replace(form, "\x00")
        if any(form in masked for form in _json_forms(sec)):
            bad.add(sec)
    return sorted(bad)


def _json_forms(text):
    """The ways a string can appear in an output file: as it is, and as it is written inside a JSON string
    (escaped quotes, backslashes and control characters; with or without non-ASCII escaped)."""
    return {text, json.dumps(text, ensure_ascii=False)[1:-1], json.dumps(text)[1:-1]}


def check_output(src, out, effective, published, texts_ok, pieces_expected, scan=None):
    """-> [(name, ok, detail)] checks run on the build output. `scan` is a name_scan() result (made here if omitted)."""
    out = Path(out)
    res = []
    html = (out / "index.html").read_text(encoding="utf-8")
    res.append(("index.html has <meta name=\"robots\" content=\"noindex\"> (or a stricter robots tag that includes noindex)", build_public.has_noindex(html), ""))
    titles = re.findall(r"<title>(.*?)</title>", strip_data_uris(html), re.S | re.I)
    res.append((f"index.html title element is exactly {build_public.PUBLIC_TITLE}", titles == [build_public.PUBLIC_TITLE], f"found {titles!r}" if titles != [build_public.PUBLIC_TITLE] else ""))
    src_html = (src.site / "index.html").read_text(encoding="utf-8")
    if build_public.OLD_FONT_RE.search(src_html):
        plain = strip_data_uris(html)
        res.append((f"index.html uses the font family {build_public.PUBLIC_FONT_FAMILY}", build_public.PUBLIC_FONT_FAMILY in plain, ""))
    scan = scan if scan is not None else name_scan(out)
    if scan["hits"]:
        res.append(("no output file, decoded data URI or decoded font table names the other project (any letter case, ASCII / UTF-16)", False, "; ".join(scan["hits"][:8])))
    elif scan["unchecked"] or scan["undecodable"]:
        # ok is None: the check did not run on the font, so it is neither a PASS nor a FAIL
        res.append(("output text and raw bytes name the other project: no hit; but the embedded font was NOT decoded, so its name table and CFF strings are UNCHECKED", None,
                    "; ".join(scan["unchecked"] + scan["undecodable"])))
    else:
        res.append(("no output file, decoded data URI or decoded font table names the other project (any letter case, ASCII / UTF-16)", True, ""))
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
    """True only for https://github.com/4444J99/versforms (an optional .git, an optional trailing slash): scheme https,
    host exactly github.com, no user name or password in the URL, no port but 443, no query or fragment, and the path
    exactly the repository. Case is ignored for host and repository, as GitHub does. ssh forms, file: paths,
    credentials and look-alike hosts (notgithub.com, github.com.example, a path or a user name that merely contains
    github.com/4444J99/versforms) are refused."""
    u = url.strip()
    if not u or re.search(r"[\s\\]", u):
        return False
    try:
        parts = urllib.parse.urlsplit(u)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme.lower() != "https" or (parts.hostname or "").lower() != "github.com" or "@" in parts.netloc:
        return False
    if port not in (None, 443) or parts.query or parts.fragment:
        return False
    if not parts.path.startswith("/") or parts.path.startswith("//"):
        return False
    path = parts.path[1:]
    path = path[:-1] if path.endswith("/") else path
    path = path[:-4] if path.lower().endswith(".git") else path
    return path.lower() == PUBLIC_REPO_NAME.lower()


def effective_url_ok(url):
    """Judges the EFFECTIVE fetch and push URLs (after url.*.insteadOf, pushInsteadOf and pushurl). In a production run this
    is exactly remote_is_public_repo. It is a module-level function so that the tests, which redirect the public repository
    to a local bare repository, can replace it; it cannot be reached from the command line or the environment."""
    return remote_is_public_repo(url)


def _redact(url):
    """A URL for a message: any user name or password is replaced (it may be a token)."""
    return re.sub(r"(?<=//)[^/@\s]*@", "***@", url)


def remote_main_sha(path):
    ls = git(path, "ls-remote", "origin", "refs/heads/main", check=False)
    return ls.stdout.split()[0] if ls.returncode == 0 and ls.stdout.split() else ""


def check_public_repo(path, branch):
    """-> [(name, ok, detail)]. Writes nothing in the repository (no fetch; ls-remote only)."""
    res = []
    p = Path(path)
    if not (p / ".git").exists():
        return [("public repo is a git checkout", False, str(path))]
    url = git(p, "config", "--get", "remote.origin.url", check=False).stdout.strip()
    res.append((f"remote origin is {PUBLIC_REPO_NAME} (https://github.com, no credentials in the URL)", remote_is_public_repo(url), _redact(url) or "no origin"))
    fetch_eff = git(p, "remote", "get-url", "origin", check=False).stdout.strip()
    push_eff = git(p, "remote", "get-url", "--push", "origin", check=False).stdout.strip()
    res.append(("effective fetch and push URL are the same (after insteadOf, pushInsteadOf and pushurl)", bool(fetch_eff) and fetch_eff == push_eff,
                "" if fetch_eff == push_eff and fetch_eff else f"fetch {_redact(fetch_eff) or '(none)'}, push {_redact(push_eff) or '(none)'}"))
    res.append((f"effective URL is {PUBLIC_REPO_NAME} on github.com", bool(fetch_eff) and effective_url_ok(fetch_eff) and effective_url_ok(push_eff), _redact(push_eff) or "no push URL"))
    push_cfg = git(p, "config", "--get-all", "remote.origin.push", check=False).stdout.strip()
    res.append(("remote.origin.push is not set (it would change what a push sends)", not push_cfg, f"remote.origin.push = {push_cfg}" if push_cfg else ""))
    cur = git(p, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    res.append(("on branch main", cur == "main", f"on {cur!r}"))
    dirty = git(p, "--no-optional-locks", "status", "--porcelain", check=False).stdout.strip()  # does not refresh .git/index
    res.append(("working tree clean", not dirty, f"{len(dirty.splitlines())} changed or untracked path(s)" if dirty else ""))
    head = git(p, "rev-parse", "HEAD", check=False).stdout.strip()
    remote = remote_main_sha(p)
    res.append(("main is fetched (local HEAD equals origin/main)", bool(remote) and remote == head, "cannot reach origin" if not remote else f"origin/main is {remote[:7]}, HEAD is {head[:7]}"))
    local_b = git(p, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
    remote_b = git(p, "ls-remote", "--heads", "origin", f"refs/heads/{branch}", check=False)
    where = [w for w, there in (("locally", local_b.returncode == 0), ("on origin", bool(remote_b.stdout.strip()))) if there]
    res.append((f"branch {branch} does not exist yet", not where, ("exists " + " and ".join(where)) if where else ""))
    return res


def commit_in_worktree(repo, build_dir, branch, message, scratch):
    """Create `branch` from main and commit exactly the build output as site/, in a TEMPORARY WORKTREE: the clone's own
    checkout (on main) is never touched, so a failure leaves nothing half-written in it. The commit is then compared with
    the build listing (paths and sizes). On success the worktree is removed and the branch stays; on failure both are
    removed and the RuntimeError says what is left. -> commit sha."""
    repo = Path(repo)
    wt_root = Path(tempfile.mkdtemp(prefix="post-poem-wt-", dir=str(scratch)))
    target = wt_root / "tree"
    created = False
    try:
        git(repo, "worktree", "add", "-b", branch, str(target), "main")
        created = True
        site = target / "site"
        if site.exists():
            shutil.rmtree(site)
        shutil.copytree(build_dir, site)
        git(target, "add", "-A", "-f", "site")  # -f: a .gitignore in the public clone must not silently drop a file
        git(target, "commit", "-m", message)
        sha = git(target, "rev-parse", "HEAD")
        committed = {}
        for line in git(target, "ls-tree", "-r", "-l", "HEAD", "--", "site").splitlines():
            meta, path = line.split("\t", 1)
            committed[path[len("site/"):]] = int(meta.split()[3])
        built = tree_listing(build_dir)
        if committed != built:
            diff = sorted(set(committed) ^ set(built)) or sorted(k for k in built if committed.get(k) != built[k])
            raise RuntimeError(f"the committed site/ differs from the build output ({len(diff)} path(s), first: {', '.join(diff[:5])})")
        return sha
    except (RuntimeError, OSError) as e:
        left = []
        try:
            git(repo, "worktree", "remove", "--force", str(target), check=False)
        except OSError:
            pass
        if created:
            r = git(repo, "branch", "-D", branch, check=False)
            left.append(f"branch {branch} " + ("removed again" if r.returncode == 0 else f"COULD NOT be removed ({r.stderr.strip()}); delete it by hand"))
        left.append(f"the checkout of {repo} was not touched (still on main, clean)")
        raise RuntimeError(f"{e}. State left: " + "; ".join(left)) from e
    finally:
        git(repo, "worktree", "remove", "--force", str(target), check=False)
        git(repo, "worktree", "prune", check=False)
        shutil.rmtree(wt_root, ignore_errors=True)


def public_changes(public_site, out):
    """Compare the public clone's current site/data/j.json with the new build.
    -> (piece ids new in the public site, already-public piece ids whose published data changed). Page placement in the
    scan atlas ('a') moves whenever the page set changes, so it does not count as a change."""
    new = json.loads((Path(out) / "data" / "j.json").read_text())
    try:
        old = json.loads((Path(public_site) / "data" / "j.json").read_text())
    except (OSError, ValueError):
        old = None
    new_pieces = {pc["id"]: pc for pc in new["pieces"]}
    if old is None:
        return list(new_pieces), []
    old_pieces = {pc["id"]: pc for pc in old["pieces"]}
    strip = lambda pg: {k: v for k, v in pg.items() if k != "a"}
    new_pages, old_pages = {pg["id"]: strip(pg) for pg in new["pages"]}, {pg["id"]: strip(pg) for pg in old["pages"]}
    added = [pid for pid in new_pieces if pid not in old_pieces]
    changed = [pid for pid, pc in new_pieces.items() if pid in old_pieces and (
        pc != old_pieces[pid] or any(new_pages.get(pg) != old_pages.get(pg) for v in pc["V"] for pg, _ in v["P"]))]
    return added, changed


# ------------------------------------------------------------------ pull request text

CONSOLE_ONLY_AUDIT = ("font file name",)  # name records of the font file can hold personal names: never in public text


def word_of(ok):
    return "UNCHECKED" if ok is None else ("PASS" if ok else "FAIL")


def render_pr_body(ctx):
    L = []
    L.append("## What changed")
    L.append(f"- Piece(s) requested: {', '.join(ctx['pids'])}")
    L.append("- New in the public site: " + (", ".join(ctx["new_pieces"]) or "none"))
    L.append("- Already public and rebuilt with changed published data: " + (", ".join(ctx["changed_pieces"]) or "none"))
    for pid in ctx["pids"]:
        v = ctx["versions"][pid]
        L.append(f"- {pid}: {v['how']}; version(s) published: {', '.join('V[%d]' % i for i in v['indices'])} of {v['total']}; "
                 f"newest in the stack: V[{v['newest']}]; top of the stack: V[{v['top']}]; corrected reviews on versions not published: {v['unpublished_corrected']}")
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
        L.append(f"- {word_of(ok)} {name}" + (f": {detail}" if detail else ""))
    for pid, c in ctx["counts"].items():
        L.append(f"- {pid} lines: {c['confirmed']} confirmed, {c['corrected']} corrected (author text published), {c['unreviewed']} without review"
                 + (f"; {c['withheld']} quotation line(s) withheld" if c.get("withheld") else ""))
    L.append(f"- sha256 of data/j.json: `{ctx['sha']}`")
    L.append("")
    L.append("## Not verified")
    L.append("- Rendering on a real phone or other device")
    L.append("- A Cloudflare Pages preview deploy of this branch")
    pg_shared = sorted({f["page"] for f in ctx["shared"]})
    L.append("- Author sign-off on shared scans: " + (f"other writing is visible in the scan of {len(pg_shared)} page(s) ({', '.join(pg_shared)}); "
                                                      "which pieces or items is in the console log of the run, not in this text" if pg_shared else "none found"))
    for note in ctx["font_notes"]:
        L.append(f"- {note}")
    for w in ctx["warnings"]:
        L.append(f"- {w}")
    L.append("- Reader-visible strings (list only; the author decides):")
    for kind, value in ctx["audit"]:
        if kind in CONSOLE_ONLY_AUDIT:
            continue  # the pull request text is public; these rows are on the console only
        L.append(f"  - {kind}: {value[:140]}")
    if any(kind in CONSOLE_ONLY_AUDIT for kind, _ in ctx["audit"]):
        L.append("  - font file name records: printed on the console of the run, not in this text")
    L.append("")
    L.append("Merging is the author's decision. To undo a post: `git revert` the merge commit in this repository.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ main flow

class _Parser(argparse.ArgumentParser):
    def error(self, message):
        """argparse exits 2 on a usage error; here 2 means 'a gate failed'. Usage errors are 64, as documented."""
        self.print_usage(sys.stderr)
        sys.stderr.write(f"{self.prog}: error: {message}\n")
        sys.exit(EXIT_USAGE)


def parse_args(argv):
    ap = _Parser(description="Gate, build and prepare a pull request for posting a poem.")
    ap.add_argument("pieces", nargs="+", metavar="PIECE_ID")
    ap.add_argument("--db", required=True, help="studio database export directory (COLLECTION/DOCID.json)")
    ap.add_argument("--public-repo", help="clone of 4444J99/versforms (required unless --dry-run)")
    ap.add_argument("--include-versions", action="store_true", help="publish the whole version stack (needs the author's approval)")
    ap.add_argument("--force", action="store_true", help="override the three gates only")
    ap.add_argument("--accept-shared-scan", action="append", default=[], metavar="IDS", help="ids of Series pieces / other-line items whose writing may show in a shared scan")
    ap.add_argument("--accept-embedded-font", action="store_true", help="only for the case where the embedded font cannot be decoded and checked (the font venv is missing): accept publishing it unchecked")
    ap.add_argument("--dry-run", action="store_true", help="run every gate and hard stop, build into scratch, write nothing in the public repo")
    ap.add_argument("--no-pr", action="store_true", help="commit the branch in the public clone but do not push or open a PR")
    ap.add_argument("--workdir", help="scratch directory for the build (default: a new post-poem-* directory under .post-poem-work/ in the private repository, which is git-ignored)")
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
        db_root, db = load_db_with_root(a.db, piece_ids=set(src.pieces))
    except Stop as e:
        say(f"FAIL  stop cannot load inputs: {e}")
        return EXIT_STOP
    say(f"export: {db_root} ({', '.join(f'{c} {len(db[c])}' for c in COLLECTIONS)})")
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
        elif own == "unknown":
            # a value that is not exactly series/reserve/archive ('Reserve', ' reserve', a list...) cannot be shown to be "not Reserve"
            record("stop", pid, "requested piece has a recognised release pool", False, f"{pool_note(db, pid)}; the studio writes exactly 'series', 'reserve' or 'archive'. --force does not override this")
        record("gate", pid, "(b) every line confirmed or corrected", *gate_verified(src, db, pid))
        record("gate", pid, "(c) in a filed or registered batch", *gate_filed(db, pid))

    # --- versions, corrections, stale transcript, shared scan
    versions, corrections, counts, warnings, shared_all = {}, {}, {}, [], []
    console_notes = []  # shown on the console only: they can name pieces that are not posted
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
            if pool in ("reserve", "archive", "unknown"):
                # a piece posted earlier and since moved to Reserve/Archive (or whose pool reads as neither Series nor Reserve) must not be rebuilt into a new public site
                record("stop", pid, "already-public piece is not in Reserve or Archive", False,
                       f"{pool_note(db, pid) if pool == 'unknown' else 'pool is ' + pool}; it is in release/public.json and would be rebuilt and published again. Take it out of release/public.json (and decide how to retire it publicly) first; --force does not override this")
            elif pool != "series":
                warnings.append(f"{pid} is already in release/public.json and is rebuilt into this site, but its release pool is {pool}. Its gates are not rechecked here; decide whether it should stay public")
    for pid in effective:
        v = versions[pid]
        say(f"versions {pid}: publishing {len(v['indices'])} of {v['total']} ({v['how']})")
        pc = src.pieces[pid]
        n_v = len(pc["V"])
        v["newest"], v["top"] = n_v - 1, pc["top"]
        v["unpublished_corrected"] = unpublished_corrections(src, db, pid, select[pid])
        if pid in pids and not a.include_versions and n_v > 1:
            ids = ", ".join(f"V[{i}] {pc['V'][i]['id']}" for i in select[pid])
            say(f"  published: {ids}; newest in the stack (last entry of V): V[{n_v - 1}] {pc['V'][n_v - 1]['id']}; top of the stack: V[{pc['top']}]; "
                f"corrected reviews on versions NOT published: {v['unpublished_corrected']}")
            if v["unpublished_corrected"]:
                warnings.append(f"{pid}: {v['unpublished_corrected']} line(s) the author corrected sit on version(s) that are not published ({', '.join('V[%d]' % i for i in range(n_v) if i not in select[pid])}); those corrections are not in the public data")
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
    used_ids = set()
    # the shared-scan stop runs over EVERY piece in the rebuilt list: the pieces already public are rebuilt too
    for pid in effective:
        finds = shared_scan(src, db, pid, select[pid], public_ids, accepted)
        shared_all.extend(f for f in finds if f["status"] != "ok" or pid in pids)
        used_ids.update(f["id"] for f in finds)
        bad = [f for f in finds if f["status"] in ("stop", "needs-accept")]
        detail = f"{len(finds)} co-resident piece(s), item(s) or facing page(s) on {len(src.pages_of(pid, select[pid]))} page(s)"
        if bad:
            detail += "; " + "; ".join(f"{f['id']} on {f['page']}: {f['reason']}" for f in bad)
        record("stop", pid, "(i) shared scan" + ("" if pid in pids else " (already public, rebuilt)"), not bad, detail)
        for f in finds:
            if f["status"] == "accepted":
                say(f"  accepted shared scan: {f['id']} on {f['page']}")
        # the scans copied for the published pages, and for their facing pages (spread image, whole-spread scans, identical files),
        # also show whatever other versions of the SAME piece are written there
        direct = src.pages_of(pid, select[pid])
        seen_pages = set(direct) | set(src.spread_mates(direct))
        sib = {pg for pg in seen_pages for q in [src.pieces[pid]]
               for vi, v in enumerate(q["V"]) if vi not in select[pid] for p2, _ in v["P"] if p2 == pg}
        if sib:
            warnings.append(f"{pid}: the scan of {', '.join(sorted(sib))} also shows writing of its unpublished version(s)")
        # an already-public piece that shares the scan: its own unpublished versions on that page show too
        for f in finds:
            if f["status"] == "ok" and f["id"] in select and f["id"] != pid:
                hidden = sorted({f["page"]} & {pg for vi, v in enumerate(src.pieces[f["id"]]["V"]) if vi not in select[f["id"]] for pg, _ in v["P"]})
                if hidden:
                    warnings.append(f"{f['id']} (already public) has unpublished version(s) written on {', '.join(hidden)}, whose scan is in this site")
    extra = sorted(accepted - used_ids)
    if extra:
        # ids of pieces that are not posted yet stay out of the pull request text: console only
        console_notes.append(f"--accept-shared-scan named ids that share no scan with any rebuilt piece: {', '.join(extra)}")
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
    # default scratch: a new directory under the repository's git-ignored .post-poem-work/, never a sibling of the repository
    if a.workdir:
        workdir = Path(a.workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        # build/ is deleted and rebuilt on every run: only ever one this script made (it leaves a marker next to it)
        if (workdir / "build").is_symlink():
            say(f"FAIL  usage {workdir / 'build'} is a symbolic link; this script replaces build/ and will not follow or delete a link. Remove the link or choose another --workdir")
            return EXIT_USAGE
        if (workdir / "build").exists() and not (workdir / WORKDIR_MARK).exists():
            say(f"FAIL  usage {workdir / 'build'} already exists and was not made by this script; it would be deleted. "
                "Name an empty directory with --workdir (or leave --workdir out), or remove that folder yourself")
            return EXIT_USAGE
    else:
        scratch = root / DEFAULT_SCRATCH  # inside the repository, git-ignored; never a sibling directory of the repository
        scratch.mkdir(parents=True, exist_ok=True)
        workdir = Path(tempfile.mkdtemp(prefix="post-poem-", dir=str(scratch)))
    (workdir / WORKDIR_MARK).write_text("made by tools/post_poem.py; build/ here is replaced by every run\n")
    out = workdir / "build"
    try:
        res = build_public.build(out, effective, site=src.site, select=select, corrections=corrections, strip_prov=True)
    except SystemExit as e:
        say(f"FAIL  stop the build was refused: {e.code if isinstance(e.code, str) else 'exit status ' + str(e.code)}")
        return EXIT_STOP
    except (ValueError, OSError) as e:
        say(f"FAIL  stop the build failed: {e}")
        return EXIT_STOP
    published = set(res["published"])
    texts_ok = {s for (pg, bi) in published for s in src.jpages[pg]["B"][bi]["L"]} | set(corrections.values())
    scan = name_scan(out)
    checks = check_output(src, out, effective, published, texts_ok, effective, scan=scan)
    font_notes = []
    for f in res["fonts"]:
        if f.get("renamed"):
            say(f"font: renamed to {build_public.PUBLIC_FONT_FAMILY} ({f['glyphs']} glyphs, {f['bytes']} -> {f['bytes_out']} bytes, {f['changed']} name/CFF record(s) rewritten)")
    # the source page names the old family: the embedded font file is then KNOWN to carry the old name
    known_old_font = bool(build_public.OLD_FONT_RE.search((src.site / "index.html").read_text(encoding="utf-8")))
    if scan["unchecked"]:
        why = ("the embedded font could not be decoded and checked for the other project's name (" + "; ".join(scan["unchecked"]) + "): "
               + (scan["reason"] or res["font_error"] or "no reason given"))
        if res["font_error"] and not scan["reason"]:
            why += f" [{res['font_error']}]"
        if known_old_font:
            # the font could not be renamed and the page's own CSS names the old family: the file carries the old name,
            # so the acceptance flag (for a font of unknown content) does not apply
            msg = ("the embedded font is known to carry the other project's name (the page's font family is that name) and it was not renamed; "
                   "--accept-embedded-font does not cover this. Install the font venv (VERSFORMS_FONT_PYTHON) and run again")
            # a dry run fails exactly as a real run does, so a script that checks the exit status is not told "fine" about input a real run refuses
            checks.append(("embedded font is renamed (the source font is known to carry the other project's name)", False, why + ". " + msg))
        elif a.dry_run:
            say(f"WARN  stop embedded font: {why}. A real run needs --accept-embedded-font.")
        else:
            checks.append(("embedded font unchecked: --accept-embedded-font given", bool(a.accept_embedded_font),
                           "" if a.accept_embedded_font else why + ". Install the font venv (VERSFORMS_FONT_PYTHON) or pass --accept-embedded-font to publish the font unchecked"))
        font_notes.append("The embedded font could not be decoded and checked here; --accept-embedded-font published it unchecked: " + "; ".join(scan["unchecked"]))
    elif scan["fonts_checked"]:
        font_notes.append(f"Embedded font(s) decoded and checked: {scan['fonts_checked']} (name table records, CFF strings, glyph names, raw table bytes); renamed in the build to {build_public.PUBLIC_FONT_FAMILY}")
    if scan["undecodable"]:
        # the venv ran and the font did not parse: a compressed WOFF2 cannot be searched as raw bytes, so nothing vouches for it
        checks.append(("every embedded font parses and passes the name check (--accept-embedded-font does not cover this)", False,
                       "; ".join(scan["undecodable"]) + ": " + (scan["reason"] or "no reason given")))
    for name, ok, detail in checks:
        say(f"{word_of(ok)}  check {name}" + (f": {detail}" if detail else ""))
    if any(ok is False for _, ok, _ in checks):
        say("\nREFUSED: the build output failed its own checks. --force does not override these.")
        return EXIT_STOP
    for pg, ids in sorted(res["shared"].items()):
        say(f"  note: {pg} also carries {sorted(ids)} — visible in the scan, text withheld")
    listing = tree_listing(out)
    sha = sha256_file(out / "data" / "j.json")
    say(f"\nbuild: {len(listing)} files, {sum(listing.values())} bytes, {len(res['pages'])} page(s), {res['applied']} correction(s) applied")
    say(f"data/j.json sha256 {sha}")
    audit = audit_strings(out)
    if scan["fonts_checked"]:
        # the font is downloadable and its other name records can hold personal names; they are on the console only
        listed = any(k == "font file name" for k, _ in audit)
        font_notes.append("Author sign-off on the embedded font file's own metadata (its name records are downloadable with the font; "
                          + ("they were listed to the author on the console and are not repeated here)" if listed else
                             "they could NOT be listed here because the font tool failed, so nobody has looked at them)"))
    say("reader-visible strings (list only):")
    for kind, value in audit:
        say(f"  {kind}: {value[:140]}")
    for kind, value in audit:
        if kind == "info panel (from prov)":
            warnings.append(f"info panel text produced from prov: {value}")
    for w in warnings:
        say(f"WARNING  {w}")
    for n in console_notes:
        say(f"NOTE  {n}")

    if a.dry_run:
        say("\nfile list:")
        for rel, size in listing.items():
            say(f"  {size:>9}  {rel}")
        say("\nDRY RUN: nothing written in the public repository, nothing pushed, release/public.json unchanged.")
        say("would write release/public.json pieces: " + ", ".join(effective))
        return EXIT_OK

    # --- public repository: branch, replace site/, commit (in a temporary worktree: the clone's checkout is never touched)
    before = tree_hashes(Path(a.public_repo) / "site")
    after = tree_hashes(out)
    diff = dict(added=[k for k in after if k not in before], changed=[k for k in after if k in before and after[k] != before[k]],
                removed=[k for k in before if k not in after], bytes=sum(sz for sz, _ in after.values()))
    new_pieces, changed_pieces = public_changes(Path(a.public_repo) / "site", out)
    # the pull request text is public: it is rendered and checked BEFORE anything is committed
    ctx = dict(pids=pids, versions=versions, pages=res["pages"], diff=diff, results=results, checks=checks,
               counts={p: counts[p] for p in pids}, sha=sha, shared=shared_all, font_notes=font_notes, warnings=warnings, audit=audit,
               new_pieces=new_pieces, changed_pieces=changed_pieces)
    body = render_pr_body(ctx)
    if OLD_NAME_RE.search(body):
        say("FAIL  stop the pull request text names the other project; nothing was committed. --force does not override this")
        return EXIT_STOP
    (workdir / "pr-body.md").write_text(body)
    try:
        sha_commit = commit_in_worktree(a.public_repo, out, branch, "Post " + ", ".join(pids), workdir)
    except (RuntimeError, OSError) as e:
        say(f"ERROR  {e}")
        return EXIT_PARTIAL
    say(f"committed {sha_commit[:7]} on branch {branch} in {a.public_repo} (the clone's checkout is still on main)")
    if a.no_pr:
        say(f"--no-pr: branch not pushed. PR text is in {workdir / 'pr-body.md'}")
        update_release_list(src, pids, all_versions, write=False)
        return EXIT_OK

    main_before = remote_main_sha(a.public_repo)
    pushed = False
    try:
        # the fully qualified refspec: what is sent does not depend on remote.origin.push or push.default
        git(a.public_repo, "push", "origin", f"refs/heads/{branch}:refs/heads/{branch}")
        pushed = True
        on_origin = git(a.public_repo, "ls-remote", "origin", f"refs/heads/{branch}", check=False).stdout.split()
        if not on_origin or on_origin[0] != sha_commit:
            raise RuntimeError(f"after the push origin does not have {branch} at {sha_commit[:7]}")
        if remote_main_sha(a.public_repo) != main_before:
            raise RuntimeError("main of the public repository CHANGED during the push; this must never happen. Look at the public repository now")
        r = subprocess.run(["gh", "pr", "create", "--repo", PUBLIC_REPO_NAME, "--base", "main", "--head", branch,
                            "--title", "Post " + ", ".join(pids), "--body-file", str(workdir / "pr-body.md")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"gh pr create failed: {r.stderr.strip()}")
        say(f"pull request: {r.stdout.strip()}")
    except (RuntimeError, OSError) as e:
        if pushed:
            say(f"ERROR  {e}\nThe branch {branch} IS pushed to origin; no pull request was created. Create it with:\n"
                f"  gh pr create --repo {PUBLIC_REPO_NAME} --base main --head {branch} --title \"Post {', '.join(pids)}\" --body-file {workdir / 'pr-body.md'}\n"
                f"Private release/public.json is NOT updated.")
        else:
            say(f"ERROR  {e}\nThe branch {branch} is committed locally in {a.public_repo} and NOT pushed; private release/public.json is NOT updated. PR text: {workdir / 'pr-body.md'}")
        return EXIT_PARTIAL

    # --- private release list (not committed): only now that the branch is pushed AND the pull request exists
    update_release_list(src, pids, all_versions, write=True)
    return EXIT_OK


def update_release_list(src, pids, all_versions, write=True):
    """Add the posted pieces to the private release/public.json. With write=False nothing is written: the intended change
    is printed instead. The write is atomic (a temporary file in the same directory, flushed, then os.replace)."""
    path = src.release_path
    old = path.read_text() if path.exists() else ""
    cur = json.loads(old) if old.strip() else {"pieces": []}
    cur["pieces"] = list(dict.fromkeys(list(cur.get("pieces", [])) + pids))
    if all_versions:
        cur["all_versions"] = [p for p in cur["pieces"] if p in all_versions]
    new = json.dumps(cur, indent=2) + "\n"
    change = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "release/public.json", "release/public.json")).rstrip()
    if not write:
        say("release/public.json was NOT changed (--no-pr). Intended change, to apply by hand once the pull request exists:")
        say(change)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".public.json.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(new)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    say(f"updated {path} (not committed):")
    say(change)


def main(argv=None):
    a = parse_args(argv)
    try:
        return run(a)
    except Stop as e:
        say(f"FAIL  stop {e}")
        return EXIT_STOP


if __name__ == "__main__":
    sys.exit(main())
