"""Cross-feature clearance binds exact output; source edits invalidate approval."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import release_contract as rc


class ReleaseContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "note.json").write_text('{"text":"technical fixture"}')
        self.sources = [{"pieceId": "p-test", "versionId": "v-test", "sourceFingerprint": rc.digest({"text": "source"})}]
        self.component = {"kind": "note", "id": "note-test", **self.sources[0], "path": "note.json",
                          "sha256": rc.file_digest(self.root / "note.json"), "revisionDigest": rc.digest({"revision": 1}), "fixture": False}
        # Synthetic records only; no real author's clearance is created.
        self.manifest = rc.prepare(self.root, sources=self.sources, components=[self.component])
        self.clearance = {"schema": rc.CLEARANCE, "status": "approved", "manifestDigest": self.manifest["manifestDigest"],
                          "execution_authority": False,
                          "author_clearance": {"actor": "synthetic-test-author", "source": "synthetic:test-only", "at": "2026-01-01T00:00:00Z", "manifestDigest": self.manifest["manifestDigest"]},
                          "pool_clearance": [{"pieceId": "p-test", "versionId": "v-test", "pool": "series", "source": "synthetic:test-only"}],
                          "evidence": {k: "synthetic:test-only" for k in ("filing_workflow", "image_exposure", "identity_metadata", "device_acceptance")}}

    def check(self, **changes):
        args = dict(root=self.root, current_sources=self.sources, component=self.component)
        args.update(changes)
        return rc.evaluate(self.manifest, self.clearance, **args)

    def test_exact_output_and_evidence_are_eligible_without_execution_authority(self):
        result = self.check()
        self.assertTrue(result["eligible"], result)
        self.assertFalse(result["execution_authority"])
        (self.root / "note.json").write_text('{"text":"changed"}')
        self.assertIn("output-bytes-changed", self.check()["reasons"])

    def test_missing_clearance_or_source_is_refused(self):
        self.assertFalse(rc.evaluate(self.manifest, None, current_sources=self.sources)["eligible"])
        self.assertFalse(self.check(current_sources=None)["eligible"])
        self.assertFalse(self.check(current_sources=[{**self.sources[0], "sourceFingerprint": rc.digest({"text": "new"})}])["eligible"])

    def test_changed_body_credit_anchor_permission_or_revision_invalidates(self):
        for field in ("text", "credit", "anchor", "permission", "sourceFingerprint"):
            changed = {**self.component, "revisionDigest": rc.digest({field: "changed"})}
            self.assertIn("component-changed-or-not-cleared", self.check(component=changed)["reasons"])

    def test_reserve_empty_evidence_and_fixtures_stay_refused(self):
        for pool in ("reserve", "archive", "unsorted"):
            c = copy.deepcopy(self.clearance); c["pool_clearance"][0]["pool"] = pool
            self.assertFalse(rc.evaluate(self.manifest, c, current_sources=self.sources)["eligible"])
        c = copy.deepcopy(self.clearance); c["evidence"]["image_exposure"] = ""
        self.assertFalse(rc.evaluate(self.manifest, c, current_sources=self.sources)["eligible"])
        self.assertIn("technical-fixture-excluded", self.check(component={**self.component, "fixture": True})["reasons"])

    def test_extra_file_symlink_and_tampered_manifest_are_refused(self):
        (self.root / "private.txt").write_text("do not ship")
        self.assertFalse(self.check()["eligible"])
        (self.root / "linked").symlink_to(self.root / "private.txt")
        with self.assertRaises(ValueError): rc.prepare(self.root, sources=self.sources)
        m = copy.deepcopy(self.manifest); m["files"][0]["bytes"] += 1
        self.assertIn("output-manifest-changed", rc.validate_manifest(m))

    def test_event_must_name_exact_output_and_preserves_original_channel_type(self):
        e = {"schema": rc.EVENT, "state": "posted", "manifestDigest": self.manifest["manifestDigest"],
             "recordedBy": "synthetic-test-author", "source": "synthetic:test-only", "at": "2026-01-01T00:00:00Z",
             "channel": "site", "url": "https://example.test/output"}
        self.assertTrue(self.check(event=e)["eligible"])
        e["manifestDigest"] = rc.digest({})
        self.assertFalse(self.check(event=e)["eligible"])
        old = {"type": "social", "url": "https://versforms.pages.dev/"}
        self.assertEqual(rc.event_channels(old)["recordedType"], "social")
        self.assertEqual(rc.event_channels(old)["channel"], "site")
        self.assertIsNone(rc.event_channels(old)["publicationClassification"])
        self.assertNotIn("pub", old)

    def test_attribution_must_be_nonempty_text(self):
        for value in (True, 1, {"actor": "unknown"}, ["unattributed"], " "):
            for field in ("actor", "source"):
                clearance = copy.deepcopy(self.clearance)
                clearance["author_clearance"][field] = value
                self.assertIn("unattributable-author-clearance", rc.evaluate(
                    self.manifest, clearance, current_sources=self.sources)["reasons"])
            clearance = copy.deepcopy(self.clearance)
            clearance["pool_clearance"][0]["source"] = value
            self.assertIn("excluded-or-unattributed-pool", rc.evaluate(
                self.manifest, clearance, current_sources=self.sources)["reasons"])

    def test_event_urls_and_invalid_calendar_values_are_refused(self):
        event = {"schema": rc.EVENT, "state": "posted", "manifestDigest": self.manifest["manifestDigest"],
                 "recordedBy": "synthetic-test-author", "source": "synthetic:test-only",
                 "at": "2026-01-01T00:00:00Z", "channel": "site", "url": "https://example.test/output"}
        for url in ("https://[", "https://example.test:garbage/", "https://example.test:65536/",
                    " https://example.test/", "https://example.test/white space", True):
            self.assertIn("invalid-publication-url", self.check(event={**event, "url": url})["reasons"])
        for at in ("2000Z", "2026-02-30T00:00:00Z", "0000-01-01T00:00:00Z", "2026-01-01T24:00:00Z"):
            self.assertIn("unbound-publication-event", self.check(event={**event, "at": at})["reasons"])
        for field in ("source", "recordedBy"):
            self.assertIn("unbound-publication-event", self.check(event={**event, field: True})["reasons"])
        self.assertEqual(rc.event_channels({"type": "social", "url": "https://["})["channel"], "social")

    def test_non_json_current_bindings_fail_closed(self):
        changed = copy.deepcopy(self.sources)
        changed[0]["sourceFingerprint"] = float("nan")
        self.assertIn("current-source-bindings-changed-or-missing", self.check(current_sources=changed)["reasons"])

    def test_empty_identity_bindings_are_refused_consistently(self):
        for key in ("pieceId", "versionId"):
            manifest = copy.deepcopy(self.manifest)
            manifest["sources"][0][key] = " "
            manifest["components"][0][key] = " "
            manifest["manifestDigest"] = rc.digest({k: v for k, v in manifest.items() if k != "manifestDigest"})
            self.assertIn("invalid-source-binding", rc.validate_manifest(manifest))
            self.assertIn("invalid-component-binding", rc.validate_manifest(manifest))
        self.assertFalse(rc.safe_path(" "))


if __name__ == "__main__":
    unittest.main()
