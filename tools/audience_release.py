#!/usr/bin/env python3
"""Validate a private weekly record against T03's exact output; never schedule."""
import argparse
import json
from pathlib import Path
import release_contract as rc


def evaluate(record, context):
    context = context or {}
    manifest = context.get("manifest")
    result = rc.evaluate(manifest, context.get("clearance"),
                         current_sources=context.get("current_sources"), root=context.get("output_root"))
    reasons = result["reasons"][:]
    if not isinstance(record, dict) or record.get("schema") != "versforms.audience-week.v1":
        reasons.append("unsupported-weekly-record")
    else:
        if record.get("is_template") is not False:
            reasons.append("unfilled-weekly-template")
        release = record.get("release") or {}
        if not isinstance(release, dict) or release.get("manifest_digest") != (manifest or {}).get("manifestDigest"):
            reasons.append("weekly-record-not-bound-to-output")
        elif manifest:
            selected = {(s["pieceId"], s["versionId"]) for s in manifest.get("sources", [])}
            requested = {(release.get("piece_id"), v) for v in release.get("version_ids", []) if isinstance(v, str)}
            if requested != selected:
                reasons.append("weekly-source-selection-changed")
        for asset in (record.get("media") or {}).get("assets", []):
            if (not isinstance(asset, dict) or not any(f.get("path") == asset.get("path") and f.get("sha256") == asset.get("sha256")
                                                    for f in (manifest or {}).get("files", []))):
                reasons.append("weekly-media-outside-cleared-output")
    return {"schema": "versforms.audience-eligibility.v1", "eligible": not reasons,
            "reasons": list(dict.fromkeys(reasons)), "manifestDigest": (manifest or {}).get("manifestDigest"),
            "may_publish": False, "may_schedule_external_actions": False,
            "limit": "Record validation only; this does not grant execution authority."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate(json.loads(args.record.read_text()), json.loads(args.context.read_text()))
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    return 0 if result["eligible"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
