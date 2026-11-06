#!/usr/bin/env python3
"""Export one stored T10 realization as a verified, static private package.

The input is an existing immutable Studio artifact revision, not a new creative
choice. Its full realization history and current glyph assets are preserved.
The package descriptor is separate from that stored revision, avoiding a
circular artifact/package digest. This command never publishes or edits inputs.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

import release_contract
import script_realizations as sr

SCHEMA = "versforms.realization-preview-package.v1"
TEMPLATE = "versforms.t10-static-preview.v1"
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_PACKAGE_BYTES = 32 * 1024 * 1024
FONT_TYPES = {".otf": "font/otf", ".ttf": "font/ttf", ".woff": "font/woff", ".woff2": "font/woff2"}
STATIC_CSP = "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; font-src data:; img-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'none'"


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def no_links(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise sr.Invalid("linked package inputs are not supported")
    return path.resolve()


def validate_artifact(artifact):
    """Validate the bounded realization-artifact vocabulary before digesting.

    Every object key and number in this vocabulary is schema-defined (ASCII
    keys, integer block indexes). Its canonical JSON agrees with Studio's
    stableJSON; arbitrary payload properties and floating numbers are refused.
    The reader independently validates the complete document with its existing
    artifact model and compares it with the selected stored revision.
    """
    sr.keys(artifact, ("schemaVersion", "family", "kind", "recordId", "revisionId",
                      "parents", "source", "payload", "fixture", "at", "by", "reason", "revisionDigest"), "artifact")
    if type(artifact["schemaVersion"]) is not int or artifact["schemaVersion"] != 1 or artifact["family"] != "artifact" or artifact["kind"] != "realization":
        raise sr.Invalid("expected a stored realization artifact")
    if not all(sr.valid_id(artifact[key]) for key in ("recordId", "revisionId")):
        raise sr.Invalid("invalid stored artifact identity")
    parents = artifact["parents"]
    if not isinstance(parents, list) or any(not sr.valid_id(p) or p == artifact["revisionId"] for p in parents) or len(set(parents)) != len(parents):
        raise sr.Invalid("invalid stored artifact parents")
    if type(artifact["fixture"]) is not bool or not release_contract.instant(artifact["at"]) or not isinstance(artifact["by"], str) or not artifact["by"].strip() or not isinstance(artifact["reason"], str):
        raise sr.Invalid("invalid stored artifact provenance")
    sr.keys(artifact["source"], ("pieceId", "versionId", "sourceFingerprint"), "artifact source")
    binding = artifact["source"]
    if not all(sr.valid_id(binding[key]) for key in ("pieceId", "versionId")) or not isinstance(binding["sourceFingerprint"], str) or not sr.HASH.fullmatch(binding["sourceFingerprint"]):
        raise sr.Invalid("invalid stored artifact source")
    sr.keys(artifact["payload"], ("realization",), "realization artifact payload")
    envelope = {"format": sr.FORMAT, "schemaVersion": 1, "realizations": [copy.deepcopy(artifact["payload"]["realization"])]}
    sr.validate(envelope)
    document = envelope["realizations"][0]
    latest = document["revisions"][-1]
    if {"pieceId": document["pieceId"], "versionId": document["versionId"], "sourceFingerprint": latest["source"]["versionFingerprint"]} != binding:
        raise sr.Invalid("stored artifact and realization sources differ")
    if any(revision["fixture"] for revision in document["revisions"]) and not artifact["fixture"]:
        raise sr.Invalid("stored artifact cannot remove technical fixture history")
    if any(type(index) is not int or index > 9007199254740991 for revision in document["revisions"] for _, indexes in revision["source"]["members"] for index in indexes):
        raise sr.Invalid("artifact block indexes must be safe integers")
    # JSON encoding also rejects lone surrogate strings before any output exists.
    body = {key: value for key, value in artifact.items() if key != "revisionDigest"}
    if not isinstance(artifact["revisionDigest"], str) or not sr.HASH.fullmatch(artifact["revisionDigest"]) or sr.digest(body) != artifact["revisionDigest"]:
        raise sr.Invalid("stored artifact digest changed")
    if len(sr.canonical(artifact).encode("utf-8")) > 64 * 1024:
        raise sr.Invalid("stored artifact exceeds 64 KiB")
    return envelope


def static_preview(projected, assets):
    """Embed the one verified font into three fixed slots of the T10 template.

    This accepts no caller HTML. The existing preview generator owns escaping,
    Unicode/layout and whole-line fallback. Unexpected template changes fail
    closed instead of enabling a general HTML or dependency rewriting path.
    """
    markup, report = sr.preview_html(projected, assets)
    font = next(a for a in projected["realizations"][0]["glyphAssets"] if a["kind"] == "font")
    path = Path(assets) / font["path"]
    mime = FONT_TYPES.get(path.suffix.lower())
    if mime is None or path.stat().st_size > 8_000_000:
        raise sr.Invalid("static preview requires a bounded supported font")
    uri = "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    old_font = "@font-face{font-family:ajp-scribbles;src:url('" + font["path"] + "');font-display:block}"
    new_font = "@font-face{font-family:ajp-scribbles;src:url('" + uri + "');font-display:block}"
    old_csp = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; font-src \'self\'; img-src \'self\' data:; base-uri \'none\'">'
    replacements = [(old_font, new_font), (old_csp, '<meta http-equiv="Content-Security-Policy" content="' + STATIC_CSP + '">'),
                    ('<html lang="en">', '<html lang="en" data-template="' + TEMPLATE + '">')]
    for old, new in replacements:
        if markup.count(old) != 1:
            raise sr.Invalid("the static T10 template changed; package adapter needs explicit review")
        markup = markup.replace(old, new, 1)
    return markup, report


def export_package(artifact, repo, db, assets, output):
    """Revalidate source, policy and assets, then publish a new local directory."""
    artifact = copy.deepcopy(artifact)
    envelope = validate_artifact(artifact)
    repo, assets = no_links(repo), no_links(assets)
    output = sr.private_destination(output)
    if output.exists() or output == repo or repo in output.parents or output == assets or assets in output.parents:
        raise sr.Invalid("package output must be a new independent private directory")
    if db is None:
        raise sr.Invalid("an explicit Studio export is required")
    db = no_links(db)
    if output == db or db in output.parents:
        raise sr.Invalid("package output overlaps the Studio export")
    document = envelope["realizations"][0]
    latest = document["revisions"][-1]
    current = sr.source_snapshot(repo, document["pieceId"], document["versionId"], db)
    binding = sr.source_binding(current)
    if binding != artifact["source"]:
        raise sr.Invalid("stored artifact source is stale; explicit rebind required")
    policy = sr.release_policy(repo, document["pieceId"], db)
    projected = sr.projection(envelope, {(document["pieceId"], document["versionId"]): current}, {document["pieceId"]: policy})
    if len(projected["realizations"]) != 1:
        reasons = [reason for row in projected.get("excluded", []) for reason in row["reasons"]]
        raise sr.Invalid("realization excluded from private package: " + ", ".join(reasons))
    declared_assets = latest["glyphAssets"]
    if len(declared_assets) > 16:
        raise sr.Invalid("private package exceeds the bounded asset count")
    files, media_types = {}, {}
    for asset in declared_assets:
        path = no_links(assets / asset["path"])
        if not path.is_file() or path.parent != assets / "assets" or path.stat().st_size > 8_000_000:
            raise sr.Invalid("expected a bounded regular glyph asset")
        payload = path.read_bytes()
        if sha(payload) != asset["sha256"]:
            raise sr.Invalid("glyph asset bytes changed")
        mime = FONT_TYPES.get(path.suffix.lower()) if asset["kind"] == "font" else "application/json" if path.suffix.lower() == ".json" else None
        if mime is None:
            raise sr.Invalid("unsupported private package asset media type")
        files[asset["path"]], media_types[asset["path"]] = payload, mime
    # Generate from copied verified inputs so no source-file race can substitute
    # a different font between its hash check and embedding/coverage inspection.
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".t10-preview-package-", dir=output.parent))
    try:
        for name, payload in files.items():
            target = temporary / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        for asset in declared_assets:
            if asset["kind"] == "capture-manifest":
                sr.read_json(temporary / asset["path"])  # Validate the copied bytes, never execute them.
        markup, _ = static_preview(projected, temporary)
        files.update({"index.html": markup.encode("utf-8"), "realization.json": encoded(envelope), "artifact.json": encoded(artifact)})
        media_types.update({"index.html": "text/html", "realization.json": "application/json", "artifact.json": "application/json"})
        if any(len(data) > MAX_FILE_BYTES for data in files.values()) or sum(map(len, files.values())) > MAX_PACKAGE_BYTES:
            raise sr.Invalid("private package byte limit exceeded")
        manifest = {"schema": SCHEMA, "schemaVersion": 1, "template": TEMPLATE,
                    "source": binding, "policy": policy,
                    "artifactRevisionId": artifact["revisionId"], "artifactDigest": artifact["revisionDigest"],
                    "realization": {"id": document["id"], "revisionId": latest["id"], "revisionDigest": latest["digest"]},
                    "entry": "index.html", "model": "realization.json", "artifact": "artifact.json",
                    "fixture": artifact["fixture"] or latest["fixture"], "may_publish": False,
                    "files": [{"path": name, "bytes": len(data), "mediaType": media_types[name], "sha256": sha(data)} for name, data in sorted(files.items())]}
        manifest_bytes = encoded(manifest)
        if len(manifest_bytes) > 64 * 1024:
            raise sr.Invalid("private package manifest exceeds 64 KiB")
        for name, data in files.items():
            (temporary / name).write_bytes(data)
        (temporary / "manifest.json").write_bytes(manifest_bytes)
        # Recheck the live binding and policy immediately before making the
        # prepared directory visible. A later change is also checked by reader.
        if sr.source_binding(sr.source_snapshot(repo, document["pieceId"], document["versionId"], db)) != binding or sr.release_policy(repo, document["pieceId"], db) != policy:
            raise sr.Invalid("source or policy changed during package preparation")
        if output.exists():
            raise sr.Invalid("package destination appeared concurrently")
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return {"schema": SCHEMA, "template": TEMPLATE, "output": str(output),
            "source": binding, "policy": policy, "artifactRevisionId": artifact["revisionId"],
            "artifactDigest": artifact["revisionDigest"], "package": {"manifestUrl": "manifest.json", "sha256": sha(manifest_bytes)},
            "files": len(files), "bytes": sum(map(len, files.values())), "fixture": manifest["fixture"], "may_publish": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=sr.ROOT)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = export_package(sr.read_json(args.artifact), args.repo, args.db, args.assets, args.out)
        print(json.dumps(result, indent=2))
        return 0
    except (sr.Invalid, OSError, KeyError, TypeError, ValueError, UnicodeError) as error:
        print("T10 package refused: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
