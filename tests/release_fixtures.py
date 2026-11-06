"""Synthetic release evidence for positive controls, never author decisions."""
import release_contract as rc


def clearance(manifest):
    return {"schema": rc.CLEARANCE, "status": "approved", "manifestDigest": manifest["manifestDigest"],
            "execution_authority": False,
            "author_clearance": {"actor": "synthetic-test-only", "source": "synthetic:test-only",
                                 "at": "2026-01-01T00:00:00Z", "manifestDigest": manifest["manifestDigest"]},
            "pool_clearance": [{"pieceId": s["pieceId"], "versionId": s["versionId"],
                                "pool": "series", "source": "synthetic:test-only"} for s in manifest["sources"]],
            "evidence": {k: "synthetic:test-only" for k in
                         ("filing_workflow", "image_exposure", "identity_metadata", "device_acceptance")}}


def context(sources, components):
    files = {c["path"]: {"path": c["path"], "bytes": 1, "sha256": c["sha256"]} for c in components}
    body = {"schema": rc.SCHEMA, "files": list(files.values()), "sources": sources,
            "components": components, "inputs": {}, "code": {}, "exposure": {"test_only": True}}
    manifest = {**body, "manifestDigest": rc.digest(body)}
    assert rc.validate_manifest(manifest) == []
    return {"manifest": manifest, "clearance": clearance(manifest), "current_sources": sources}


def regions(manifest):
    import source_regions as sr
    bindings = [{"pieceId": p, "versionId": v, "sourceFingerprint": rc.digest({"synthetic-source": [p, v]})}
                for p, v in sorted({(a["piece_id"], a["version_id"]) for a in manifest["atoms"]})]
    sha = "sha256:" + sr.manifest_digest(manifest)
    components = [{"kind": "regions", "id": sr.region_component_id(s["pieceId"], s["versionId"]),
                   **s, "revisionDigest": sha, "fixture": False, "path": "regions.json", "sha256": sha}
                  for s in bindings]
    return context(bindings, components)
