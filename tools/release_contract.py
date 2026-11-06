#!/usr/bin/env python3
"""Exact-output release contracts; validation never performs publication.

The authority is an independently supplied, attributable author record. Hashes
bind its scope; they are not a signature and do not authenticate its author.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit
from release_canonical import canonical

SCHEMA = "versforms.release-output.v1"
CLEARANCE = "versforms.release-clearance.v1"
EVENT = "versforms.release-event.v1"
HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
KINDS = {"note", "contribution", "audio", "realization", "regions", "media"}


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_path(value):
    return (text(value) and "\\" not in value
            and not any(ord(c) < 32 or ord(c) == 127 for c in value)
            and not value.startswith("/") and not value.endswith("/")
            and all(p not in {"", ".", "..", ".git"} for p in value.split("/"))
            and PurePosixPath(value).as_posix() == value)


def inventory(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("Output must be a real directory")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Linked output is not eligible: " + str(path))
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if not safe_path(rel):
                raise ValueError("Unsafe output path: " + rel)
            files.append({"path": rel, "bytes": path.stat().st_size, "sha256": file_digest(path)})
    return files


def prepare(root, *, sources, components=(), inputs=None, code=None, exposure=None):
    """Inventory existing private output. No clearance or event is manufactured."""
    body = {"schema": SCHEMA, "files": inventory(root), "sources": copy.deepcopy(sources),
            "components": copy.deepcopy(list(components)), "inputs": copy.deepcopy(inputs or {}),
            "code": copy.deepcopy(code or {}), "exposure": copy.deepcopy(exposure or {})}
    body["manifestDigest"] = digest(body)
    errors = validate_manifest(body)
    if errors:
        raise ValueError("; ".join(errors))
    return body


def validate_manifest(manifest):
    errors = []
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA:
        return ["unsupported-output-manifest"]
    unsigned = {k: v for k, v in manifest.items() if k != "manifestDigest"}
    try:
        calculated = digest(unsigned)
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return ["invalid-output-json"]
    if manifest.get("manifestDigest") != calculated:
        errors.append("output-manifest-changed")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return errors + ["empty-output-inventory"]
    paths = set()
    for item in files:
        if (not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}
                or not safe_path(item.get("path")) or type(item.get("bytes")) is not int
                or item["bytes"] < 0 or not HASH.fullmatch(str(item.get("sha256", "")))):
            errors.append("invalid-output-entry")
            continue
        if item["path"] in paths:
            errors.append("duplicate-output-path")
        paths.add(item["path"])
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        return errors + ["missing-source-bindings"]
    keys = set()
    fingerprints = {}
    for source in sources:
        if (not isinstance(source, dict) or not all(text(source.get(k))
                for k in ("pieceId", "versionId", "sourceFingerprint"))
                or not HASH.fullmatch(source["sourceFingerprint"])):
            errors.append("invalid-source-binding")
            continue
        key = (source["pieceId"], source["versionId"])
        if key in keys:
            errors.append("duplicate-source-binding")
        keys.add(key)
        fingerprints[key] = source["sourceFingerprint"]
    components = manifest.get("components")
    if not isinstance(components, list):
        return errors + ["invalid-component-list"]
    seen = set()
    for component in components:
        if not isinstance(component, dict):
            errors.append("invalid-component")
            continue
        identity_valid = all(text(component.get(k)) for k in ("kind", "id", "pieceId", "versionId"))
        key = (component.get("kind"), component.get("id")) if identity_valid else None
        source_key = (component.get("pieceId"), component.get("versionId")) if identity_valid else None
        if (not identity_valid or component.get("kind") not in KINDS or not component.get("id") or key in seen
                or not HASH.fullmatch(str(component.get("revisionDigest", "")))
                or not HASH.fullmatch(str(component.get("sourceFingerprint", "")))
                or type(component.get("fixture")) is not bool
                or source_key not in keys
                or fingerprints.get(source_key) != component.get("sourceFingerprint")):
            errors.append("invalid-component-binding")
        seen.add(key)
        output = next((f for f in files if isinstance(f, dict) and f.get("path") == component.get("path")), None)
        if output is None or output.get("sha256") != component.get("sha256"):
            errors.append("component-output-not-in-manifest")
    return list(dict.fromkeys(errors))


def text(value):
    return isinstance(value, str) and bool(value.strip())


def instant(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z", value):
        return False
    try:
        return dt.datetime.fromisoformat(value[:-1] + "+00:00").tzinfo is not None
    except ValueError:
        return False


def publication_url(value):
    if not text(value) or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    try:
        url = urlsplit(value)
        # Accessing .port validates syntax and range; parsing alone does not.
        port = url.port
        return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password
    except ValueError:
        return False


def same_json(left, right):
    try:
        return canonical(left) == canonical(right)
    except (ValueError, TypeError, UnicodeError, OverflowError):
        return False


def evaluate(manifest, clearance, *, root=None, current_sources=None, component=None, event=None):
    """Return exact record eligibility; outward execution needs its own authority.

    current_sources is mandatory. A valid historical manifest does not prove
    that the source currently selected by a consumer still has those bytes.
    """
    reasons = validate_manifest(manifest)
    if reasons:
        return {"eligible": False, "reasons": reasons}
    if current_sources is None or not same_json(current_sources, manifest["sources"]):
        reasons.append("current-source-bindings-changed-or-missing")
    if root is not None:
        try:
            if inventory(root) != manifest["files"]:
                reasons.append("output-bytes-changed")
        except (ValueError, OSError):
            reasons.append("output-unavailable-or-linked")
    if not isinstance(clearance, dict) or clearance.get("schema") != CLEARANCE:
        reasons.append("missing-author-clearance")
    else:
        if clearance.get("status") != "approved" or clearance.get("manifestDigest") != manifest["manifestDigest"]:
            reasons.append("clearance-does-not-cover-output")
        author = clearance.get("author_clearance") or {}
        if (not isinstance(author, dict) or not text(author.get("actor")) or not text(author.get("source"))
                or not instant(author.get("at")) or author.get("manifestDigest") != manifest["manifestDigest"]):
            reasons.append("unattributable-author-clearance")
        if clearance.get("execution_authority") is not False:
            reasons.append("record-must-not-imply-execution-authority")
        selected = {(s["pieceId"], s["versionId"]) for s in manifest["sources"]}
        pools = clearance.get("pool_clearance") or []
        if (not isinstance(pools, list) or len(pools) != len(selected)
                or any(not isinstance(p, dict) or not all(isinstance(p.get(k), str) for k in ("pieceId", "versionId")) for p in pools)
                or {(p["pieceId"], p["versionId"]) for p in pools} != selected):
            reasons.append("incomplete-pool-clearance")
        elif any(not isinstance(p, dict) or p.get("pool") != "series" or not text(p.get("source")) for p in pools):
            reasons.append("excluded-or-unattributed-pool")
        required = ("filing_workflow", "image_exposure", "identity_metadata", "device_acceptance")
        evidence = clearance.get("evidence") or {}
        if not isinstance(evidence, dict) or any(not isinstance(evidence.get(k), str) or not evidence[k].strip() for k in required):
            reasons.append("incomplete-release-evidence")
    if component is not None:
        found = next((c for c in manifest["components"] if isinstance(component, dict) and c.get("kind") == component.get("kind") and c.get("id") == component.get("id")), None)
        if found is None or not same_json(found, component):
            reasons.append("component-changed-or-not-cleared")
        if not isinstance(component, dict) or component.get("fixture") is not False:
            reasons.append("technical-fixture-excluded")
    if any(c.get("fixture") is not False for c in manifest["components"]):
        reasons.append("technical-fixture-excluded")
    if event is not None:
        if (not isinstance(event, dict) or event.get("schema") != EVENT
                or event.get("manifestDigest") != manifest["manifestDigest"]
                or event.get("state") != "posted" or not text(event.get("source"))
                or not text(event.get("recordedBy")) or not instant(event.get("at"))
                or event.get("channel") not in {"site", "social"}):
            reasons.append("unbound-publication-event")
        else:
            if not publication_url(event.get("url")):
                reasons.append("invalid-publication-url")
    return {"eligible": not reasons, "reasons": list(dict.fromkeys(reasons)),
            "manifestDigest": manifest["manifestDigest"], "execution_authority": False}


def event_channels(record):
    """Read existing event semantics without rewriting history or legal meaning."""
    raw = record.get("type")
    try:
        hostname = urlsplit(str(record.get("url", ""))).hostname
    except ValueError:
        hostname = None
    channel = record.get("channel")
    if channel not in {"site", "social"}:
        channel = "site" if hostname in {"versforms.pages.dev", "vers.forms", "www.vers.forms"} else ("social" if raw == "social" else None)
    return {"recordedType": raw, "channel": channel, "url": record.get("url"),
            "publicationClassification": None, "classificationProvenance": "author-decision-pending"}
