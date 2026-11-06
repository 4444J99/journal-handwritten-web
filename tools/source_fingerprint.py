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
    """Exact release/media binding; calculating it grants no clearance."""
    return {"pieceId": source["pieceId"], "versionId": source["versionId"],
            "sourceFingerprint": source_fingerprint(source)}
