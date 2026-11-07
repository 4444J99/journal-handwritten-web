"""T02 logical source hashes, shared by source, notes, media and script consumers.

Only explicit IDs, exact membership, text, block type and stanza boundaries
participate. Pixel/geometry digests belong to the separate asset contract.
v1 is for history inspection; callers must explicitly rebind to v2.
"""
from __future__ import annotations

import hashlib
import json


def logical_source_payload(source, version=2):
    if version not in (1, 2):
        raise ValueError("unsupported logical source fingerprint version")
    fields = ("lineId", "text", "blockType")
    if version == 2:
        if any(type(line.get("breakBefore")) is not bool for line in source["lines"]):
            raise ValueError("v2 source lines require explicit breakBefore")
        fields += ("breakBefore",)
    return {"pieceId": source["pieceId"], "versionId": source["versionId"],
            "members": source["members"], "lines": [
                {key: line[key] for key in fields} for line in source["lines"]]}


def source_fingerprint(source, version=2):
    value = json.dumps(logical_source_payload(source, version), sort_keys=True,
                       ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_fingerprint_v1(source):
    return source_fingerprint(source, 1)


def source_binding(source):
    """Current v2 release/media binding, never a silent historical rebind.

    A raw logical payload may be bound explicitly. A preserved snapshot that
    already declares a digest must agree with v2; callers retain v1 history and
    create a new explicit rebind instead of treating its old digest as current.
    """
    if not isinstance(source, dict):
        raise ValueError("current source snapshot must be an object")
    lines = source.get("lines")
    if not isinstance(lines, list) or not lines or any(
            not isinstance(line, dict) or not isinstance(line.get("lineId"), str) or not line["lineId"]
            or not isinstance(line.get("text"), str) or not isinstance(line.get("blockType"), str)
            or line.get("transcriptionStatus") == "untranscribed" for line in lines):
        raise ValueError("current source needs explicit transcribed lines")
    if len({line["lineId"] for line in lines}) != len(lines):
        raise ValueError("duplicate current source line ID")
    current = source_fingerprint(source)
    if source.get("fingerprintVersion", 2) != 2:
        raise ValueError("current source requires explicit v2 rebind")
    for key in ("versionFingerprint", "sourceFingerprint"):
        if key in source and source[key] != current:
            raise ValueError("current source is stale or requires explicit v2 rebind")
    return {"pieceId": source["pieceId"], "versionId": source["versionId"],
            "sourceFingerprint": current}
