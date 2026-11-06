#!/usr/bin/env python3
"""Private, append-only script realizations; never edits a poem or publishes it.

The fixture command copies an existing reading verbatim. It does not translate,
transliterate, infer a language choice, rebuild a font, or accept author decisions.
See docs/t10-script-realizations.md for the bounded T02/T03 integration contract.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
FORMAT = "versforms-script-realizations"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
HASH = re.compile(r"sha256:[a-f0-9]{64}\Z")
LANGUAGE = re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*\Z")
SCRIPT = re.compile(r"[A-Z][a-z]{3}\Z")
MAX_BYTES = 4_000_000
SCOPES = {"private", "withheld", "public-proposed"}
MODES = {"translation", "transliteration", "visual-realization"}
CHANGES = {"initial", "script-change", "source-rebind", "realization-edit", "visibility-change"}


class Invalid(ValueError):
    """Input is ambiguous, malformed, stale, or outside the pilot boundary."""


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Invalid("duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise Invalid("expected a bounded regular JSON file")
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid("non-finite JSON")))
    except (UnicodeError, ValueError, RecursionError) as error:
        raise Invalid("invalid UTF-8 JSON") from error


def keys(value, expected, where):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise Invalid(where + ": missing or unknown fields")


def valid_id(value):
    return isinstance(value, str) and ID.fullmatch(value) is not None


def scalar_text(value, *, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()) or len(value) > 16000:
        raise Invalid("expected bounded Unicode text")
    # Source/realized lines are explicit records. Never hide line breaks or bidi
    # overrides inside them. ZWJ/ZWNJ remain valid for scripts that require them.
    for char in value:
        cp = ord(char)
        if unicodedata.category(char) in {"Cc", "Cs"} or cp in {0x2028, 0x2029} or 0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069:
            raise Invalid("control or bidi formatting character in text; use layout fields")
    return value


def valid_instant(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise Invalid("timestamp must be a UTC ISO instant")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise Invalid("invalid timestamp") from error


def _unique(items, key, what):
    result = {}
    for item in items:
        if not isinstance(item, dict) or not valid_id(item.get(key)) or item[key] in result:
            raise Invalid("invalid or duplicate " + what)
        result[item[key]] = item
    return result


def source_fingerprint_v1(source):
    # Historical v1 fingerprint: stanza boundaries (breakBefore) were ignored.
    # Retained for readable history and explicit migration/rebind only.
    return digest({"pieceId": source["pieceId"], "versionId": source["versionId"],
                   "members": source["members"], "lines": [
                       {k: line[k] for k in ("lineId", "text", "blockType")}
                       for line in source["lines"]]})


def source_fingerprint(source):
    # v2 logical-structure digest: includes stanza boundaries (breakBefore).
    # Coordinates, page dimensions, and display order do not define identity.
    return digest({"pieceId": source["pieceId"], "versionId": source["versionId"],
                   "members": source["members"], "lines": [
                       {k: line[k] for k in ("lineId", "text", "blockType", "breakBefore")}
                       for line in source["lines"]]})


def private_db(path, piece_ids):
    """Read an export for private work, preserving an empty release collection.

    post_poem's publication loader intentionally refuses an unsorted export. The
    private fixture may inspect it, but never turns absence into release clearance.
    Reuse its exact collection/release-name checks, then parse strict JSON here.
    """
    import post_poem
    try:
        root = post_poem.find_db_root(Path(path))
        post_poem.check_export_names(root, piece_ids)
        result = {name: {} for name in post_poem.COLLECTIONS}
        for name in post_poem.COLLECTIONS:
            folder = root / name
            if folder.exists() and (folder.is_symlink() or not folder.is_dir()):
                raise Invalid("linked or invalid export collection")
            for file in sorted(folder.glob("*.json")):
                value = read_json(file)
                if not isinstance(value, dict):
                    raise Invalid("studio document must be an object")
                result[name][file.stem] = value
        return result
    except post_poem.Stop as error:
        raise Invalid("invalid studio export names") from error


def source_snapshot(repo, piece_id, version_id, db=None):
    """Exact existing membership plus current, attributable exported corrections."""
    repo = Path(repo)
    paths = ["site/data/j.json", "studio/data/review.json"]
    site, review = [read_json(repo / p) for p in paths]
    pieces = _unique(site["pieces"], "id", "piece")
    _unique([v for p in site["pieces"] for v in p["V"]], "id", "version")
    pages = _unique(review["pages"], "id", "page")
    _unique([l for p in review["pages"] for b in p["blocks"] for l in b["lines"]], "id", "line")
    version = next((v for v in pieces.get(piece_id, {}).get("V", []) if v["id"] == version_id), None)
    if version is None:
        raise Invalid("unknown exact piece/version")
    corrections = {}
    if db is not None:
        # Reuse the current strict export loader (including malformed release-name
        # hard stops). Importing it has no publication/network side effects.
        corrections = private_db(db, set(pieces))["reviews"]
    rows, seen, review_evidence = [], set(), []
    for member in version["P"]:
        if not isinstance(member, list) or len(member) != 2 or member[0] not in pages or not isinstance(member[1], list):
            raise Invalid("invalid source membership")
        page_id, blocks = member
        for bi in blocks:
            if type(bi) is not int or bi < 0 or bi >= len(pages[page_id]["blocks"]) or (page_id, bi) in seen:
                raise Invalid("missing or duplicate source block")
            seen.add((page_id, bi))
            block = pages[page_id]["blocks"][bi]
            for li, line in enumerate(block["lines"]):
                original = scalar_text(line["tx"], empty=True)
                text = original
                correction = corrections.get(line["id"])
                if correction is not None:
                    if not isinstance(correction, dict):
                        raise Invalid("invalid line review")
                    review_evidence.append({"lineId": line["id"], "digest": digest(correction)})
                    if block.get("t") != "quotation" and correction.get("status") == "corrected":
                        if not isinstance(correction.get("original"), str) or not isinstance(correction.get("text"), str):
                            raise Invalid("malformed corrected review")
                        if correction["original"] != original and correction["text"] != original:
                            raise Invalid("stale correction; source must be resolved explicitly")
                        text = scalar_text(correction["text"], empty=True)
                rows.append({"lineId": line["id"], "text": text, "originalText": original,
                             "blockType": block.get("t") or "text", "breakBefore": bool(rows) and li == 0})
    if not rows:
        raise Invalid("empty source version")
    snapshot = {"pieceId": piece_id, "versionId": version_id, "members": copy.deepcopy(version["P"]),
                "lines": rows, "versionFingerprint": "", "provenance": {
                    "repository": "4444J99/journal-handwritten-web", "contract": "T05-proposed-fingerprint-v2",
                    "files": [{"path": p, "sha256": file_hash(repo / p)} for p in paths],
                    "reviewRecords": review_evidence,
                    "readingStatus": "existing-transcription-with-exported-corrections; not a new author verification"}}
    snapshot["versionFingerprint"] = source_fingerprint(snapshot)
    return snapshot


def release_policy(repo, piece_id, db=None):
    """Read current sort; unknown or malformed values never become Series."""
    import post_poem
    src = post_poem.Source(repo)
    if piece_id not in src.pieces:
        raise Invalid("unknown source piece")
    data = {"release": {}} if db is None else private_db(db, set(src.pieces))
    record = data["release"].get(piece_id, {})
    if not isinstance(record, dict):
        raise Invalid("invalid source release record")
    pool = record.get("pool", "unsorted")
    visibility = record.get("publicStatus", "private")
    if pool not in {"series", "reserve", "archive", "unsorted"} or visibility not in {"private", "withheld", "public"}:
        raise Invalid("unknown source release pool or visibility")
    return {"pool": pool, "visibility": visibility}


def seal(revision):
    revision = copy.deepcopy(revision)
    revision.pop("digest", None)
    revision["digest"] = digest(revision)
    return revision


def _validate_source(source, piece_id, version_id):
    keys(source, ("pieceId", "versionId", "members", "lines", "versionFingerprint", "provenance"), "source")
    if source["pieceId"] != piece_id or source["versionId"] != version_id:
        raise Invalid("a realization cannot change its editorial piece/version")
    if not isinstance(source["members"], list) or not source["members"]:
        raise Invalid("empty membership")
    seen = set()
    for member in source["members"]:
        if not isinstance(member, list) or len(member) != 2 or not valid_id(member[0]) or not isinstance(member[1], list) or not member[1]:
            raise Invalid("invalid membership")
        for bi in member[1]:
            if type(bi) is not int or bi < 0 or (member[0], bi) in seen:
                raise Invalid("invalid or repeated membership")
            seen.add((member[0], bi))
    if not isinstance(source["lines"], list) or not source["lines"]:
        raise Invalid("empty source lines")
    _unique(source["lines"], "lineId", "source line")
    for line in source["lines"]:
        keys(line, ("lineId", "text", "originalText", "blockType", "breakBefore"), "source line")
        scalar_text(line["text"], empty=True)
        scalar_text(line["originalText"], empty=True)
        scalar_text(line["blockType"])
        if type(line["breakBefore"]) is not bool:
            raise Invalid("invalid stanza boundary")
    if source["versionFingerprint"] not in (source_fingerprint(source), source_fingerprint_v1(source)):
        raise Invalid("source fingerprint differs from its preserved snapshot")
    provenance = source["provenance"]
    keys(provenance, ("repository", "contract", "files", "reviewRecords", "readingStatus"), "source provenance")
    for field in ("repository", "contract", "readingStatus"):
        scalar_text(provenance[field])
    if not isinstance(provenance["files"], list) or not provenance["files"] or not isinstance(provenance["reviewRecords"], list):
        raise Invalid("missing source evidence")
    for file in provenance["files"]:
        keys(file, ("path", "sha256"), "source file")
        scalar_text(file["path"])
        if not isinstance(file["sha256"], str) or not HASH.fullmatch(file["sha256"]):
            raise Invalid("invalid source file hash")
    for record in provenance["reviewRecords"]:
        keys(record, ("lineId", "digest"), "review evidence")
        if not valid_id(record["lineId"]) or not isinstance(record["digest"], str) or not HASH.fullmatch(record["digest"]):
            raise Invalid("invalid review evidence")


def validate(envelope):
    """Structural and semantic validation; hashes detect change, not permission."""
    keys(envelope, ("format", "schemaVersion", "realizations"), "envelope")
    if envelope["format"] != FORMAT or type(envelope["schemaVersion"]) is not int or envelope["schemaVersion"] != 1 or not isinstance(envelope["realizations"], list):
        raise Invalid("unsupported realization envelope")
    _unique(envelope["realizations"], "id", "realization")
    all_revision_ids = set()
    asset_paths = {}
    for document in envelope["realizations"]:
        keys(document, ("id", "pieceId", "versionId", "revisions"), "realization")
        if not valid_id(document["pieceId"]) or not valid_id(document["versionId"]) or not isinstance(document["revisions"], list) or not document["revisions"]:
            raise Invalid("invalid realization identity/history")
        previous = None
        for revision in document["revisions"]:
            keys(revision, ("id", "parent", "at", "actor", "change", "source", "language", "script", "mode", "method", "authors", "lines", "layout", "glyphAssets", "visibility", "fixture", "digest"), "revision")
            if not valid_id(revision["id"]) or revision["id"] in all_revision_ids:
                raise Invalid("invalid or duplicate revision id")
            all_revision_ids.add(revision["id"])
            valid_instant(revision["at"])
            scalar_text(revision["actor"])
            if revision["parent"] != (previous["digest"] if previous else None):
                raise Invalid("missing parent or forked realization history")
            if previous and revision["at"] < previous["at"]:
                raise Invalid("revision time moved backwards")
            if revision["change"] not in CHANGES or ((previous is None) != (revision["change"] == "initial")):
                raise Invalid("invalid change classification")
            _validate_source(revision["source"], document["pieceId"], document["versionId"])
            if not isinstance(revision["language"], str) or not LANGUAGE.fullmatch(revision["language"]) or not isinstance(revision["script"], str) or not SCRIPT.fullmatch(revision["script"]):
                raise Invalid("expected language tag and ISO 15924 script-code syntax")
            if revision["mode"] not in MODES or type(revision["fixture"]) is not bool or revision["visibility"] not in SCOPES:
                raise Invalid("invalid method/fixture/visibility")
            method = revision["method"]
            keys(method, ("kind", "evidence", "normalization"), "method")
            if method["kind"] not in {"unchanged-source-fixture", "human-supplied"} or method["normalization"] != "preserve":
                raise Invalid("unsupported realization method or normalization")
            scalar_text(method["evidence"])
            if not isinstance(revision["authors"], list) or not revision["authors"]:
                raise Invalid("authorship is required")
            roles = set()
            for author in revision["authors"]:
                keys(author, ("id", "role", "evidence"), "author")
                if not valid_id(author["id"]) or author["role"] not in {"source-author", "realizer", "technical-fixture"}:
                    raise Invalid("invalid authorship declaration")
                scalar_text(author["evidence"])
                roles.add(author["role"])
            if "source-author" not in roles or (method["kind"] == "human-supplied" and "realizer" not in roles):
                raise Invalid("missing source/realization authorship")
            if not isinstance(revision["lines"], list) or not revision["lines"]:
                raise Invalid("realization has no lines")
            _unique(revision["lines"], "id", "realized line")
            source_ids = {line["lineId"] for line in revision["source"]["lines"]}
            for line in revision["lines"]:
                keys(line, ("id", "sourceLineIds", "text", "breakBefore"), "realized line")
                scalar_text(line["text"], empty=True)
                if not isinstance(line["sourceLineIds"], list) or not line["sourceLineIds"] or any(not isinstance(x, str) or x not in source_ids for x in line["sourceLineIds"]) or len(set(line["sourceLineIds"])) != len(line["sourceLineIds"]):
                    raise Invalid("line must reference unambiguous members of the source version")
                if type(line["breakBefore"]) is not bool:
                    raise Invalid("invalid realized stanza boundary")
            if method["kind"] == "unchanged-source-fixture":
                expected = [(line["text"], [line["lineId"]], line["breakBefore"]) for line in revision["source"]["lines"]]
                actual = [(line["text"], line["sourceLineIds"], line["breakBefore"]) for line in revision["lines"]]
                if not revision["fixture"] or revision["mode"] != "visual-realization" or actual != expected or "technical-fixture" not in roles:
                    raise Invalid("verbatim fixture must retain the exact source, labels, and method")
            keys(revision["layout"], ("direction", "writingMode"), "layout")
            if revision["layout"]["direction"] not in {"ltr", "rtl"} or revision["layout"]["writingMode"] not in {"horizontal-tb", "vertical-rl", "vertical-lr"}:
                raise Invalid("unsupported layout")
            if not isinstance(revision["glyphAssets"], list):
                raise Invalid("glyph assets must be a list")
            _unique(revision["glyphAssets"], "id", "glyph asset")
            for asset in revision["glyphAssets"]:
                keys(asset, ("id", "kind", "path", "sha256", "visibility", "author", "sourceLocator"), "glyph asset")
                p = asset["path"]
                if not isinstance(p, str) or not re.fullmatch(r"assets/[A-Za-z0-9_.-]+", p) or asset["kind"] not in {"font", "capture-manifest"}:
                    raise Invalid("invalid glyph asset path/kind")
                if not isinstance(asset["sha256"], str) or not HASH.fullmatch(asset["sha256"]) or asset["visibility"] not in SCOPES:
                    raise Invalid("invalid glyph hash/visibility")
                scalar_text(asset["author"])
                scalar_text(asset["sourceLocator"])
                if p in asset_paths and asset_paths[p] != asset["sha256"]:
                    raise Invalid("asset path reused for different bytes; retain a new immutable asset path")
                asset_paths[p] = asset["sha256"]
            if seal(revision)["digest"] != revision["digest"]:
                raise Invalid("revision digest mismatch")
            if previous:
                script_changed = (revision["language"], revision["script"]) != (previous["language"], previous["script"])
                source_changed = revision["source"]["versionFingerprint"] != previous["source"]["versionFingerprint"]
                if script_changed and source_changed:
                    raise Invalid("source rebind and script change need distinct revisions")
                if script_changed != (revision["change"] == "script-change") or source_changed != (revision["change"] == "source-rebind"):
                    raise Invalid("change kind does not distinguish source edits from script edits")
                if revision["change"] == "visibility-change":
                    omitted = {"id", "parent", "at", "actor", "change", "digest", "visibility"}
                    if {k: v for k, v in revision.items() if k not in omitted} != {k: v for k, v in previous.items() if k not in omitted}:
                        raise Invalid("visibility-only revision changed content")
            previous = revision
    return envelope


def fixture(source, asset, at="2026-11-05T23:00:00Z"):
    revision = seal({"id": "t10-latn-fixture-r1", "parent": None, "at": at, "actor": "T10-tooling",
        "change": "initial", "source": copy.deepcopy(source), "language": "en", "script": "Latn",
        "mode": "visual-realization", "method": {"kind": "unchanged-source-fixture", "normalization": "preserve",
        "evidence": "T10 technical fixture: exact source reading; no translation, transliteration, language adoption, or author acceptance"},
        "authors": [{"id": "4444J99", "role": "source-author", "evidence": "existing journal source; transcription uncertainty retained"},
                    {"id": "T10-tooling", "role": "technical-fixture", "evidence": "verbatim source copied by deterministic fixture command"}],
        "lines": [{"id": f"t10-line-{i:03}", "sourceLineIds": [line["lineId"]], "text": line["text"], "breakBefore": line["breakBefore"]}
                  for i, line in enumerate(source["lines"])],
        "layout": {"direction": "ltr", "writingMode": "horizontal-tb"}, "glyphAssets": [copy.deepcopy(asset)],
        "visibility": "private", "fixture": True})
    return validate({"format": FORMAT, "schemaVersion": 1, "realizations": [{"id": "t10-p001-latn-fixture",
        "pieceId": source["pieceId"], "versionId": source["versionId"], "revisions": [revision]}]})


def projection(envelope, current_sources, policies, *, audience="private", release_context=None):
    """Small render DTO. Storage/history/provenance never leaks into a public DTO.

    Public output needs attributable clearance for the exact output inventory.
    A public-proposed label is not an authorization mechanism.
    """
    validate(envelope)
    if audience not in {"private", "public"}:
        raise Invalid("unknown projection audience")
    output, exclusions = [], []
    for doc in envelope["realizations"]:
        rev = doc["revisions"][-1]
        key = (doc["pieceId"], doc["versionId"])
        current = current_sources.get(key)
        policy = policies.get(doc["pieceId"])
        reasons = []
        if current is None:
            reasons.append("missing-source")
        else:
            _validate_source(current, doc["pieceId"], doc["versionId"])
            if current["versionFingerprint"] != rev["source"]["versionFingerprint"]:
                reasons.append("source-changed")
        if not isinstance(policy, dict) or set(policy) != {"pool", "visibility"} or policy["pool"] not in {"series", "reserve", "archive", "unsorted"} or policy["visibility"] not in {"private", "withheld", "public"}:
            reasons.append("unknown-source-policy")
        else:
            if policy["pool"] in {"reserve", "archive"}:
                reasons.append("excluded-source-pool")
            if policy["visibility"] == "withheld":
                reasons.append("withheld-source")
        if rev["visibility"] == "withheld":
            reasons.append("withheld-realization")
        if any(asset["visibility"] == "withheld" for asset in rev["glyphAssets"]):
            reasons.append("withheld-glyph-asset")
        if audience == "public":
            import release_contract
            context = release_context or {}
            manifest = context.get("manifest")
            approved = next((c for c in (manifest or {}).get("components", [])
                             if c.get("kind") == "realization" and c.get("id") == doc["id"]), None)
            if approved is None or current is None:
                reasons.append("exact-output-manifest-missing-realization")
            else:
                component = {**approved, "pieceId": doc["pieceId"], "versionId": doc["versionId"],
                             "sourceFingerprint": current["versionFingerprint"],
                             "revisionDigest": rev["digest"], "fixture": rev["fixture"]}
                bindings = [{**s, "sourceFingerprint": (current_sources.get((s["pieceId"], s["versionId"])) or {}).get("versionFingerprint")}
                            for s in manifest.get("sources", [])]
                checked = release_contract.evaluate(manifest, context.get("clearance"),
                    current_sources=bindings, component=component, root=context.get("output_root"))
                reasons.extend(checked["reasons"])
                for asset in rev["glyphAssets"]:
                    if not any(f.get("path") == asset["path"] and f.get("sha256") == asset["sha256"] for f in manifest.get("files", [])):
                        reasons.append("glyph-bytes-not-in-output-manifest")
            if not policy or policy.get("pool") != "series" or policy.get("visibility") != "public":
                reasons.append("source-not-cleared-public-series")
            if rev["fixture"]:
                reasons.append("technical-fixture")
            if rev["visibility"] != "public-proposed":
                reasons.append("private-realization")
            if any(asset["visibility"] != "public-proposed" for asset in rev["glyphAssets"]):
                reasons.append("private-glyph-asset")
        if reasons:
            exclusions.append({"id": doc["id"], "reasons": reasons})
            continue
        item = {"id": doc["id"], "revisionId": rev["id"], "revisionDigest": rev["digest"],
                       "pieceId": doc["pieceId"], "versionId": doc["versionId"],
                       **{k: copy.deepcopy(rev[k]) for k in ("language", "script", "mode", "layout", "lines", "glyphAssets", "fixture")}}
        if audience == "public":
            item["glyphAssets"] = [{k: asset[k] for k in ("id", "kind", "path", "sha256")}
                                   for asset in rev["glyphAssets"]]
        output.append(item)
    result = {"format": "versforms-script-projection", "schemaVersion": 1, "audience": audience,
              "realizations": output}
    if audience == "private":
        result["excluded"] = exclusions
    return result


def private_destination(destination):
    destination = Path(destination).absolute()
    if any(p.is_symlink() for p in [destination, *destination.parents]):
        raise Invalid("linked output paths are not supported")
    # Collapse '..' only after checking the supplied path for symlinks. Guard
    # custom --repo destinations too, not just this checkout's publishing dirs.
    destination = Path(os.path.abspath(destination))
    if any(part.casefold() in {"site", "studio", "release", "releases", "dist", "public"} for part in destination.parts):
        raise Invalid("private artifacts cannot be written to publishing inputs")
    return destination


def restore(envelope, directory):
    """Append immutable revision files. Conflicts preflight before any write.

    Interrupted imports retain complete previously written records and are
    idempotently retryable. Existing history is never overwritten or deleted.
    """
    validate(envelope)
    directory = private_destination(directory)
    # Serialize cooperating writers across the whole preflight/append. Exclusive
    # file creation alone cannot prevent concurrent forks with different IDs.
    # A directory lock leaves no lockfile and is released after process failure.
    try:
        import fcntl
    except ImportError as error:
        raise Invalid("private restore requires POSIX advisory locking") from error
    directory.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Invalid("private store is busy; retry after the active restore") from error
        return _restore_locked(envelope, directory)
    finally:
        os.close(descriptor)


def _restore_locked(envelope, directory):
    planned = []
    for doc in envelope["realizations"]:
        for revision in doc["revisions"]:
            path = directory / (revision["id"] + ".json")
            record = {"realizationId": doc["id"], "pieceId": doc["pieceId"], "versionId": doc["versionId"], "revision": revision}
            if path.exists():
                if read_json(path) != record:
                    raise Invalid("immutable revision collision")
            else:
                planned.append((path, record))
    # Validate the union before adding a suffix: catches forks under new IDs,
    # orphan histories, and repurposing an existing realization association.
    existing = pack(directory) if directory.exists() else {"format": FORMAT, "schemaVersion": 1, "realizations": []}
    merged = {d["id"]: copy.deepcopy(d) for d in existing["realizations"]}
    for doc in envelope["realizations"]:
        if doc["id"] in merged:
            old = merged[doc["id"]]
            if (old["pieceId"], old["versionId"]) != (doc["pieceId"], doc["versionId"]) or old["revisions"] != doc["revisions"][:len(old["revisions"])]:
                if old == doc:
                    continue
                raise Invalid("restore must extend identical history; branching/rewrites refused")
        merged[doc["id"]] = doc
    validate({"format": FORMAT, "schemaVersion": 1, "realizations": list(merged.values())})
    directory.mkdir(parents=True, exist_ok=True)
    for path, record in planned:
        # A complete temporary file becomes visible atomically. link() is
        # exclusive: concurrent writers cannot overwrite an immutable revision.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory.parent,
                                         prefix=".t10-revision-", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        finally:
            temp.unlink()
    return {"added": len(planned), "totalRevisions": sum(len(d["revisions"]) for d in merged.values())}


def pack(directory):
    directory = private_destination(directory)
    if not directory.is_dir():
        raise Invalid("missing private store")
    documents = {}
    for path in sorted(directory.iterdir()):
        if path.suffix != ".json":
            raise Invalid("unexpected private store entry")
        record = read_json(path)
        keys(record, ("realizationId", "pieceId", "versionId", "revision"), "stored revision")
        if not isinstance(record["revision"], dict) or path.stem != record["revision"].get("id"):
            raise Invalid("stored revision filename mismatch")
        rid = record["realizationId"]
        if not valid_id(rid):
            raise Invalid("invalid stored realization id")
        document = documents.setdefault(rid, {"id": rid, "pieceId": record["pieceId"], "versionId": record["versionId"], "revisions": []})
        if (document["pieceId"], document["versionId"]) != (record["pieceId"], record["versionId"]):
            raise Invalid("conflicting stored source association")
        document["revisions"].append(record["revision"])
    for document in documents.values():
        remaining, ordered, parent = document["revisions"][:], [], None
        while remaining:
            matches = [r for r in remaining if r.get("parent") == parent]
            if len(matches) != 1:
                raise Invalid("missing parent or forked private history")
            revision = matches[0]
            ordered.append(revision)
            remaining.remove(revision)
            parent = revision.get("digest")
        document["revisions"] = ordered
    return validate({"format": FORMAT, "schemaVersion": 1, "realizations": [documents[k] for k in sorted(documents)]})


def _font_coverage(path):
    from fontTools.ttLib import TTFont
    with TTFont(path, recalcTimestamp=False) as font:
        return set((font.getBestCmap() or {}).keys())


def preview_html(projected, asset_root):
    """Generate a private static preview: escaped text, no network or JS needed.

    Whole lines fall back when any scalar lacks a glyph. This avoids splitting a
    base/mark or shaping run across fonts. Cmap coverage is not a shaping proof.
    """
    if projected.get("audience") != "private" or len(projected.get("realizations", [])) != 1:
        raise Invalid("private preview requires exactly one eligible realization")
    record = projected["realizations"][0]
    fonts = [a for a in record["glyphAssets"] if a["kind"] == "font"]
    if len(fonts) != 1:
        raise Invalid("bounded preview requires one font asset")
    font_asset = fonts[0]
    root = Path(asset_root).resolve()
    for asset in record["glyphAssets"]:
        path = root / asset["path"]
        if path.is_symlink() or not path.is_file() or path.resolve().parent != root / "assets" or file_hash(path) != asset["sha256"]:
            raise Invalid("glyph asset missing, linked, or changed")
    font_path = root / font_asset["path"]
    coverage = _font_coverage(font_path)
    rows, fallback = [], []
    for line in record["lines"]:
        missing = [ord(c) for c in line["text"] if not c.isspace() and ord(c) not in coverage]
        css = ("stanza " if line["breakBefore"] else "") + ("fallback" if missing else "author-font")
        if missing:
            fallback.append({"lineId": line["id"], "codepoints": [f"U+{c:04X}" for c in sorted(set(missing))]})
        rows.append(f'<div class="line {css}" data-line-id="{line["id"]}">{html.escape(line["text"]) or "<br>"}</div>')
    heading = "Technical fixture — verbatim source; no translation or language adoption" if record["fixture"] else "Private author-supplied realization — not cleared for release"
    metadata = {k: record[k] for k in ("id", "revisionId", "revisionDigest", "pieceId", "versionId", "language", "script", "mode", "fixture")}
    metadata["fallbackRuns"] = fallback
    language, direction, writing = record["language"], record["layout"]["direction"], record["layout"]["writingMode"]
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; font-src 'self'; img-src 'self' data:; base-uri 'none'">
<title>T10 private technical preview</title><style>
@font-face{{font-family:ajp-scribbles;src:url('{font_asset["path"]}');font-display:block}}
:root{{color-scheme:light dark;--paper:#f2eee6;--ink:#25241e;--rule:#b4ad9d}}
@media(prefers-color-scheme:dark){{:root{{--paper:#181a1b;--ink:#e7e1d5;--rule:#66645c}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif}}
main{{max-width:900px;margin:auto;padding:70px 6vw 120px;overflow:auto}}
#realization{{font-size:clamp(19px,3vw,32px);line-height:1.65;writing-mode:{writing};text-align:start;unicode-bidi:isolate}}
.line{{white-space:pre-wrap;overflow-wrap:normal;word-break:normal;hyphens:none;min-height:1.65em}}
.stanza{{margin-block-start:1.1em}}.author-font{{font-family:ajp-scribbles,serif;font-kerning:normal;font-variant-ligatures:normal}}
.fallback{{font-family:serif}}details{{position:absolute;right:18px;top:18px;max-width:min(92vw,680px);max-height:80vh;overflow:auto;background:var(--paper);border:1px solid var(--rule);border-radius:10px;padding:10px}}
summary{{cursor:pointer;list-style:none;font-size:21px}}details[open]{{padding:20px}}details p{{line-height:1.5}}pre{{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}}h1{{font-size:18px}}
.qa{{font-size:40px;line-height:1.8}}@media print{{details{{position:static}}main{{padding:1cm}}}}
</style></head><body><main><article id="realization" lang="{language}" dir="{direction}" data-script="{record["script"]}" aria-label="Private script realization">{''.join(rows)}</article></main>
<details id="details"><summary aria-label="Show fixture details">⋯</summary><h1>{heading}</h1>
<p>Source readings and exported corrections are preserved. This is a private tooling preview, not a final poem selection. This evidence panel is hidden until requested.</p>
<pre id="metadata">{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre>
<p>Unicode diagnostics below are test characters, separate from the poem. Neither test adds characters to the author font. The complete run uses the system serif fallback where author coverage is absent.</p>
<div class="qa fallback" id="nfd-probe" lang="en" dir="ltr">A&#x301;</div><div class="qa fallback" id="nfc-probe" lang="en" dir="ltr">&#xC1;</div>
<p>NFD: U+0041 U+0301 · NFC: U+00C1. Stored text is not normalized. Both runs remain intact for browser shaping. RTL and vertical layouts require a script-specific acceptance pass after author selection.</p>
</details></body></html>''', {"fallbackRuns": fallback, "lineCount": len(rows), "fontSha256": font_asset["sha256"]}


def make_pilot(repo, db, font, output, source_locator, *, piece_id="p001", version_id="p001-diary1-0", at=None):
    output = private_destination(output)
    if output.exists():
        raise Invalid("pilot output must be new")
    font = Path(font)
    if font.is_symlink() or not font.is_file() or font.stat().st_size > 8_000_000:
        raise Invalid("expected a bounded regular author font")
    _font_coverage(font)
    source = source_snapshot(repo, piece_id, version_id, db)
    font_digest = file_hash(font)
    asset = {"id": "existing-author-font", "kind": "font", "path": "assets/font-" + font_digest[7:] + ".otf", "sha256": font_digest,
             "visibility": "private", "author": "4444J99; existing derived font, not new glyph authorship",
             "sourceLocator": source_locator}
    # A recorded instant can reproduce the exact checked fixture. Without it a
    # fresh engineering run receives its actual time; neither is author assent.
    at = at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    envelope = fixture(source, asset, at)
    sources, policies = {(piece_id, version_id): source}, {piece_id: release_policy(repo, piece_id, db)}
    projected = projection(envelope, sources, policies)
    if not projected["realizations"]:
        raise Invalid("source/realization excluded from private fixture")
    (output / "assets").mkdir(parents=True)
    shutil.copyfile(font, output / asset["path"])
    restore(envelope, output / "store")
    restored = pack(output / "store")
    if canonical(envelope) != canonical(restored):
        raise Invalid("private round trip changed data")
    preview, rendering = preview_html(projection(restored, sources, policies), output)
    (output / "index.html").write_text(preview, encoding="utf-8")
    (output / "realization.json").write_text(json.dumps(restored, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = projection(restored, sources, policies, audience="public")
    # The public DTO contains no private identifiers or exclusion diagnostics.
    (output / "public-projection.json").write_text(json.dumps({"format": public["format"], "schemaVersion": 1, "realizations": public["realizations"]}, indent=2) + "\n")
    report = {"fixture": True, "fixtureAt": at, "sourcePieceId": piece_id, "sourceVersionId": version_id,
              "sourceFingerprint": source["versionFingerprint"], "revisionDigest": envelope["realizations"][0]["revisions"][0]["digest"],
              "roundTripEqual": True, "publicRecordCount": len(public["realizations"]),
              "publicExcludedReasons": ["exact-output-manifest-missing-realization", "technical-fixture",
                                        "private-realization", "private-glyph-asset"], "rendering": rendering,
              "authorLanguageDecision": "pending", "translationProduced": False}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def render_private(envelope, repo, db, assets, output):
    """Revalidate live source/policy and immutable assets before each new preview."""
    validate(envelope)
    output = private_destination(output)
    assets = Path(assets).resolve()
    if output.exists() or output.parent.resolve() != assets:
        raise Invalid("preview must be a new file beside its existing private assets directory")
    sources, policies = {}, {}
    for doc in envelope["realizations"]:
        sources[(doc["pieceId"], doc["versionId"])] = source_snapshot(repo, doc["pieceId"], doc["versionId"], db)
        policies[doc["pieceId"]] = release_policy(repo, doc["pieceId"], db)
    projected = projection(envelope, sources, policies)
    markup, report = preview_html(projected, assets)
    with output.open("x", encoding="utf-8") as handle:
        handle.write(markup)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("fixture", help="verbatim private English/Latin fixture, not author selection")
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--font", type=Path, required=True)
    p.add_argument("--source-locator", required=True)
    p.add_argument("--at", help="recorded UTC instant for exact fixture reproduction; default is now")
    p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("validate")
    p.add_argument("envelope", type=Path)
    p = sub.add_parser("restore")
    p.add_argument("envelope", type=Path)
    p.add_argument("directory", type=Path)
    p = sub.add_parser("pack")
    p.add_argument("directory", type=Path)
    p.add_argument("output", type=Path)
    p = sub.add_parser("preview", help="recheck source/policy/assets and render one private realization")
    p.add_argument("envelope", type=Path)
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "fixture":
            result = make_pilot(args.repo, args.db, args.font, args.out, args.source_locator, at=args.at)
        elif args.command == "validate":
            validate(read_json(args.envelope))
            result = {"valid": True}
        elif args.command == "restore":
            result = restore(read_json(args.envelope), args.directory)
        elif args.command == "preview":
            result = render_private(read_json(args.envelope), args.repo, args.db, args.assets, args.out)
        else:
            envelope = pack(args.directory)
            output = private_destination(args.output)
            with output.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n")
            result = {"packed": True}
        print(json.dumps(result, indent=2))
        return 0
    except (Invalid, OSError, KeyError, TypeError, ValueError) as error:
        print(f"T10: {type(error).__name__}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
