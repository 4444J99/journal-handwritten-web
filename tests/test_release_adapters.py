"""Synthetic cross-feature positive controls and stale-output refusals."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]
import release_contract as rc
import release_fixtures as rf
import source_regions as regions
import script_realizations as scripts
import audience_release
from test_script_realizations import envelope, latest, reseal
from test_source_regions import cleared_policy


class CrossFeatureRelease(unittest.TestCase):
    def test_regions_require_exact_output_and_reject_changed_geometry(self):
        manifest = json.loads((ROOT / "docs/pilots/t08-p001/p001.source-regions.json").read_text())
        policy = cleared_policy(manifest)
        self.assertFalse(regions.evaluate(manifest, policy, "public-release")["allowed"])
        context = rf.regions(manifest)
        self.assertTrue(regions.evaluate(manifest, policy, "public-release", release_context=context)["allowed"])
        changed = copy.deepcopy(manifest)
        changed["atoms"][0]["region"]["bbox"][0] += 1
        # Old region approval fails even if its local policy is freshly rebound.
        self.assertFalse(regions.evaluate(changed, cleared_policy(changed), "public-release", release_context=context)["allowed"])
        stale = copy.deepcopy(context); stale["current_sources"][0]["sourceFingerprint"] = rc.digest({"changed": True})
        self.assertFalse(regions.evaluate(manifest, policy, "public-release", release_context=stale)["allowed"])

    def test_scripts_bind_source_revision_and_every_glyph_asset(self):
        value = envelope("TECHNICAL TEST SUPPLIED REALIZATION")
        revision = latest(value)
        revision["fixture"] = False
        revision["method"]["kind"] = "human-supplied"
        revision["authors"] = [{"id": "test-source-author", "role": "source-author", "evidence": "synthetic:test-only"},
                               {"id": "test-realizer", "role": "realizer", "evidence": "synthetic:test-only"}]
        revision["visibility"] = "public-proposed"
        revision["glyphAssets"][0]["visibility"] = "public-proposed"
        reseal(value); revision = latest(value)
        doc = value["realizations"][0]
        sources = [{"pieceId": doc["pieceId"], "versionId": doc["versionId"], "sourceFingerprint": revision["source"]["versionFingerprint"]}]
        component = {"kind": "realization", "id": doc["id"], **sources[0], "revisionDigest": revision["digest"],
                     "fixture": False, "path": "realization.json", "sha256": rc.digest(value)}
        context = rf.context(sources, [component])
        current = {(doc["pieceId"], doc["versionId"]): revision["source"]}
        policies = {doc["pieceId"]: {"pool": "series", "visibility": "public"}}
        self.assertEqual(scripts.projection(value, current, policies, audience="public", release_context=context)["realizations"], [])
        glyph = revision["glyphAssets"][0]
        manifest = context["manifest"]
        manifest["files"].append({"path": glyph["path"], "sha256": glyph["sha256"], "bytes": 1})
        manifest["manifestDigest"] = rc.digest({k: v for k, v in manifest.items() if k != "manifestDigest"})
        context["clearance"] = rf.clearance(manifest)
        out = scripts.projection(value, current, policies, audience="public", release_context=context)
        self.assertEqual(len(out["realizations"]), 1)
        self.assertNotIn("sourceLocator", json.dumps(out))
        self.assertNotIn("authors", json.dumps(out))
        changed = copy.deepcopy(value); latest(changed)["lines"][0]["text"] += " CHANGED"; reseal(changed)
        self.assertEqual(scripts.projection(changed, current, policies, audience="public", release_context=context)["realizations"], [])
        context["clearance"] = None
        self.assertEqual(scripts.projection(value, current, policies, audience="public", release_context=context)["realizations"], [])

    def test_weekly_record_binds_exact_media_without_authorizing_scheduling(self):
        sources = [{"pieceId": "p-test", "versionId": "v-test", "sourceFingerprint": rc.digest({"source": 1})}]
        component = {"kind": "media", "id": "test-media", **sources[0], "revisionDigest": rc.digest({"media": 1}),
                     "fixture": False, "path": "media.png", "sha256": rc.digest({"bytes": 1})}
        context = rf.context(sources, [component])
        record = {"schema": "versforms.audience-week.v1", "is_template": False,
                  "release": {"piece_id": "p-test", "version_ids": ["v-test"], "manifest_digest": context["manifest"]["manifestDigest"]},
                  "media": {"assets": [{"path": component["path"], "sha256": component["sha256"]}]}}
        result = audience_release.evaluate(record, context)
        self.assertTrue(result["eligible"], result)
        self.assertFalse(result["may_publish"])
        self.assertFalse(result["may_schedule_external_actions"])
        record["media"]["assets"][0]["sha256"] = rc.digest({"changed": 1})
        self.assertFalse(audience_release.evaluate(record, context)["eligible"])


if __name__ == "__main__":
    unittest.main()
