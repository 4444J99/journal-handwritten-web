"""T02 acceptance: preserved source, exact reviews, staged ingest and recovery.

All new prose, photos and extra revisions are explicit technical fixtures in
temporary directories. No test mutates the author's source or contacts a host.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import source_foundation as sf
import source_fingerprint as fp
import script_realizations as scripts
import post_poem


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sf.encoded(value))


class PreservedSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        canonical = ROOT / sf.CANONICAL
        cls.source = sf.read_json(canonical) if canonical.exists() else sf.reconstruct(ROOT)
        cls.source["reviews"] = {"current": {}, "history": []}

    def test_capture_retains_counts_ids_both_quotation_forms_and_original_bytes(self):
        source = self.source
        counts = sf.validate(source)
        self.assertEqual((counts["pages"], counts["pieces"], counts["versions"], counts["lines"]), (123, 126, 156, 2190))
        original = {v["path"]: v["sha256"] for v in source["provenance"]["sourceFiles"]}
        for name, data in zip(sf.SOURCE_FILES, sf.render_data(source, overlays=False)):
            self.assertEqual(sf.sha(sf.encoded(data, compact=True)), original[name], name)
        quotation = next(l for l in source["lines"] if l["id"] == "diary2-1-0")
        self.assertNotEqual(quotation["originalText"], quotation["readerOriginalText"])

    def test_all_38_reviews_are_validated_applied_and_idempotent_without_changing_originals(self):
        original_lines = copy.deepcopy(self.source["lines"])
        applied, report = sf.apply_reviews(self.source, ROOT / "exports/studio-db-2026-11-05")
        self.assertEqual(len(report["changed"]), 38)
        self.assertEqual(sum(r["status"] == "corrected" for r in report["changed"]), 5)
        self.assertEqual(sum(r["status"] == "confirmed" for r in report["changed"]), 33)
        self.assertEqual(applied["lines"], original_lines)
        again, second = sf.apply_reviews(applied, ROOT / "exports/studio-db-2026-11-05")
        self.assertEqual(applied, again)
        self.assertEqual(second["changed"], [])
        self.assertEqual(len(second["unchanged"]), 38)
        self.assertEqual(len(again["reviews"]["history"]), 38)
        reader, studio = sf.render_data(applied)
        self.assertEqual(len(reader["acceptedReadings"]), 5)
        self.assertEqual(len(studio["acceptedReviews"]), 38)
        self.assertEqual(len(reader["sourceBindings"]), 156)
        binding = reader["sourceBindings"]["p001/p001-diary1-0"]
        self.assertEqual(binding, {"pieceId": "p001", "versionId": "p001-diary1-0",
                                  "sourceFingerprint": "sha256:17a2950bf426bc437f00ef97c550c2ef017c734b7d50bf20c4606a01907b9a1b"})
        self.assertEqual(reader["sourceAnchors"]["diary1-2-3"], {"status": "unavailable", "reason": "no-source-line-geometry"})
        line = next(l for p in studio["pages"] for b in p["blocks"] for l in b["lines"] if l["id"] == "diary1-2-3")
        self.assertIsNone(line["box"])
        self.assertEqual(sf.logical_snapshot(applied, "p001", "p001-diary1-0")["sourceFingerprint"],
                         "sha256:17a2950bf426bc437f00ef97c550c2ef017c734b7d50bf20c4606a01907b9a1b")

    def test_geometry_and_pixels_do_not_change_logical_digest_but_invalidate_geometry_digest(self):
        source = copy.deepcopy(self.source)
        logical = sf.logical_snapshot(source, "p001", "p001-diary1-0")["sourceFingerprint"]
        geometry = sf.geometry_fingerprint(source, "diary1")
        next(l for l in source["lines"] if l["id"] == "diary1-0-0")["geometry"]["studioBox"][0] += .01
        self.assertEqual(sf.logical_snapshot(source, "p001", "p001-diary1-0")["sourceFingerprint"], logical)
        self.assertNotEqual(sf.geometry_fingerprint(source, "diary1"), geometry)
        source = copy.deepcopy(self.source)
        next(a for a in source["assets"] if a["path"] == "site/img/p/diary1.jpg")["sha256"] = "sha256:" + "0" * 64
        self.assertEqual(sf.logical_snapshot(source, "p001", "p001-diary1-0")["sourceFingerprint"], logical)
        self.assertNotEqual(sf.geometry_fingerprint(source, "diary1"), geometry)

    def test_entity_array_order_does_not_reassign_identity_or_reading_order(self):
        changed = copy.deepcopy(self.source)
        for name in ("pages", "blocks", "lines", "pieces", "versions"):
            changed[name].reverse()
        self.assertEqual(sf.render_data(changed), sf.render_data(self.source))
        self.assertEqual(sf.geometry_fingerprint(changed, "diary1"), sf.geometry_fingerprint(self.source, "diary1"))

    def test_posting_stale_original_guard_still_sees_all_preserved_reviews(self):
        src = post_poem.Source(ROOT)
        reviews = {p.stem: sf.read_json(p) for p in (ROOT / "exports/studio-db-2026-11-05/reviews").glob("*.json")}
        corrections, counts, stale = post_poem.load_corrections(src, {"reviews": reviews}, "p001", [0, 1])
        self.assertEqual(stale, [])
        self.assertEqual(len(corrections), 5)
        self.assertEqual(counts["corrected"], 5)
        self.assertEqual(counts["confirmed"], 33)


class SyntheticRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="t02-source-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root, self.db = self.base / "repository", self.base / "studio-state"
        self.db.mkdir()
        self.reader = {"v": 2, "pages": [{"id": "fixture-page", "iw": 96, "ih": 64, "W": 96, "H": 64,
            "c": [0, 0, 1, 1], "sp": None, "u": [], "a": None,
            "B": [{"t": 0, "L": ["[TECHNICAL FIXTURE] alpha", "[TECHNICAL FIXTURE] beta"], "g": [0, 0, 0], "v": 0}],
            "x": [[0, 0, .1, .1, .8, .3, .25, .1]], "pl": None}], "groups": [], "atlas": [],
            "pieces": [{"id": "fixture-piece", "V": [{"id": "fixture-version", "s": "j", "P": [["fixture-page", [0]]], "d": None}], "top": 0}],
            "prov": {"verified": False}}
        self.studio = {"version": 1, "pages": [{"id": "fixture-page", "seq": 1, "w": 96, "h": 64,
            "img": "img/fixture-page.jpg", "thumb": "img/thumbs/fixture-page.jpg", "spread": None, "uncertain": [],
            "blocks": [{"t": "text", "spread": False, "note": "", "lines": [
                {"id": "fixture-line-a", "tx": "[TECHNICAL FIXTURE] alpha", "box": [.1, .1, .8, .3]},
                {"id": "fixture-line-b", "tx": "[TECHNICAL FIXTURE] beta", "box": None}]}]}],
            "items": [{"id": "fixture-piece", "versions": [{"page": "fixture-page", "blocks": [0]}]}], "flagged": []}
        write_json(self.root / sf.SOURCE_FILES[0], self.reader)
        write_json(self.root / sf.SOURCE_FILES[1], self.studio)
        (self.root / "site/index.html").write_text("<html>Current reader technical fixture</html>\n")
        (self.root / "studio/index.html").write_text("<html>Current Release tab technical fixture</html>\n")
        self.source = sf.reconstruct(self.root)
        write_json(self.root / sf.CANONICAL, self.source)
        for name in ("reviews", "decisions", "versions", "release", "batches", "rconfig", "notes", "contributions", "artifacts", "future_history"):
            (self.db / name).mkdir()
        write_json(self.db / "reviews/fixture-line-a.json", {"at": "2026-11-06T00:00:00.000Z", "status": "confirmed", "original": "[TECHNICAL FIXTURE] alpha"})
        # Preserve forks and opaque future histories byte-for-byte, without
        # inventing an application-specific schema or collapsing to heads.
        for name in ("notes", "contributions", "artifacts", "future_history"):
            for suffix, parents in (("base", []), ("left", ["base"]), ("right", ["base"])):
                write_json(self.db / name / (suffix + ".json"), {"fixture": True, "revisionId": suffix, "parents": parents, "body": "[TECHNICAL FIXTURE] " + name})

    def test_dry_run_safe_apply_backup_restore_and_second_noop(self):
        before = (self.root / sf.CANONICAL).read_bytes()
        proposed, report = sf.apply_reviews(self.source, self.db)
        self.assertEqual(len(report["changed"]), 1)
        self.assertEqual((self.root / sf.CANONICAL).read_bytes(), before)
        backup = self.base / "pre-application"
        sf.commit_proposal(self.root, self.db, proposed, backup, expected_digest=sf.digest(self.source))
        restored = self.base / "restored"
        receipt = sf.restore(backup, restored)
        self.assertEqual((restored / "repository" / sf.CANONICAL).read_bytes(), before)
        self.assertIn("artifacts", receipt["collections"])
        self.assertIn("future_history", receipt["collections"])
        for path in sf.all_files(self.db):
            self.assertEqual(path.read_bytes(), (restored / "studio-state" / path.relative_to(self.db)).read_bytes())
        again, second = sf.apply_reviews(sf.read_json(self.root / sf.CANONICAL), self.db)
        self.assertEqual(second["changed"], [])
        self.assertEqual(sf.commit_proposal(self.root, self.db, again, None), {"changed": False, "backup": None})
        self.assertEqual(sf.rebuild(proposed, self.root, write=True)["templatesModified"], [])
        self.assertEqual(sf.rebuild(proposed, self.root, write=True)["changed"], [])
        self.assertEqual((self.root / "studio/index.html").read_text(), "<html>Current Release tab technical fixture</html>\n")

    def test_additional_correction_binds_source_without_replacing_originals_or_history(self):
        first, _ = sf.apply_reviews(self.source, self.db)
        write_json(self.db / "reviews/fixture-line-b.json", {"at": "2026-11-06T01:00:00.000Z", "status": "corrected", "original": "[TECHNICAL FIXTURE] beta", "text": "[TECHNICAL FIXTURE] corrected beta"})
        second, report = sf.apply_reviews(first, self.db)
        self.assertEqual([r["lineId"] for r in report["changed"]], ["fixture-line-b"])
        self.assertEqual(second["lines"], self.source["lines"])
        self.assertEqual(len(second["reviews"]["history"]), 2)
        sf.rebuild(second, self.root, write=True)
        script = scripts.source_snapshot(self.root, "fixture-piece", "fixture-version")
        expected = sf.logical_snapshot(second, "fixture-piece", "fixture-version")
        self.assertEqual(script["versionFingerprint"], expected["sourceFingerprint"])
        self.assertEqual(script["lines"][1]["originalText"], "[TECHNICAL FIXTURE] beta")
        self.assertEqual(script["lines"][1]["text"], "[TECHNICAL FIXTURE] corrected beta")

    def test_photo_stage_and_new_version_round_trip_keep_unknown_text_geometry_and_clearance(self):
        from PIL import Image
        photo = self.base / "synthetic-photo.jpg"
        Image.new("RGB", (96, 64), (32, 64, 96)).save(photo, "JPEG")
        descriptor = {"pieceId": "fixture-piece", "versionId": "fixture-new-version", "pageId": "fixture-new-page",
                      "blockId": "fixture-new-block", "lineId": "fixture-new-line", "fixture": True}
        staged, assets = sf.stage_photo(self.source, descriptor, photo)
        repeated, repeated_assets = sf.stage_photo(self.source, descriptor, photo)
        self.assertEqual(staged, repeated)
        self.assertEqual(assets, repeated_assets)
        self.assertEqual(staged["lines"][-1]["originalText"], None)
        self.assertEqual(staged["lines"][-1]["geometry"]["studioBox"], None)
        self.assertTrue(all(a["clearance"] is None for a in staged["assets"]))
        self.assertFalse(any(a["generative"] for a in staged["assets"]))
        sf.commit_proposal(self.root, self.db, staged, self.base / "pre-photo", assets=assets, expected_digest=sf.digest(self.source))
        sf.rebuild(staged, self.root, write=True)
        reader = sf.read_json(self.root / sf.SOURCE_FILES[0])
        studio = sf.read_json(self.root / sf.SOURCE_FILES[1])
        self.assertEqual(reader["pieces"][0]["V"][-1]["id"], "fixture-new-version")
        self.assertEqual(reader["pages"][-1]["B"][0]["L"], [""])
        self.assertEqual(reader["pages"][-1]["B"][0]["lineIds"], ["fixture-new-line"])
        self.assertEqual(reader["pages"][-1]["B"][0]["g"], [0, 1, 0])
        self.assertEqual(reader["pages"][-1]["B"][0]["v"], 1)
        self.assertIn(["fixture-new-page"], reader["groups"])
        self.assertNotIn("fixture-piece/fixture-new-version", reader["sourceBindings"])
        self.assertIsNone(reader["pages"][-1]["a"])
        self.assertEqual(studio["pages"][-1]["blocks"][0]["lines"][0]["transcriptionStatus"], "untranscribed")
        with self.assertRaisesRegex(scripts.Invalid, "untranscribed"):
            scripts.source_snapshot(self.root, "fixture-piece", "fixture-new-version")
        sf.backup(self.root, self.db, self.base / "post-photo")
        sf.restore(self.base / "post-photo", self.base / "independent-photo")
        restored_root = self.base / "independent-photo/repository"
        restored_source = sf.read_json(restored_root / sf.CANONICAL)
        self.assertEqual(sf.rebuild(restored_source, restored_root)["changed"], [])
        for asset in restored_source["assets"]:
            self.assertEqual(sf.sha((restored_root / asset["path"]).read_bytes()), asset["sha256"])
        self.assertEqual((restored_root / "source/ingest/fixture-new-page/original.jpg").read_bytes(), photo.read_bytes())

    def test_stale_reviews_and_unbacked_or_concurrent_application_fail_before_mutation(self):
        document = {"at": "2026-11-06T00:00:00Z", "status": "corrected", "original": "stale", "text": "[TECHNICAL FIXTURE] alpha"}
        write_json(self.db / "reviews/fixture-line-a.json", document)
        with self.assertRaisesRegex(sf.Invalid, "stale review"):
            sf.apply_reviews(self.source, self.db)
        proposed = copy.deepcopy(self.source)
        proposed["provenance"]["fixture"] = True
        with self.assertRaisesRegex(sf.Invalid, "backup destination"):
            sf.commit_proposal(self.root, self.db, proposed, None)
        with self.assertRaisesRegex(sf.Invalid, "changed after the proposal"):
            sf.commit_proposal(self.root, self.db, proposed, self.base / "unused", expected_digest="sha256:" + "0" * 64)
        self.assertFalse((self.base / "unused").exists())
        self.assertEqual(sf.read_json(self.root / sf.CANONICAL), self.source)

    def test_recapture_refuses_accepted_overlays_and_paths_require_strings(self):
        studio = copy.deepcopy(self.studio)
        studio["acceptedReviews"] = {"fixture-line-a": {"original": "[TECHNICAL FIXTURE] alpha", "status": "confirmed", "at": "2026-11-06T00:00:00Z"}}
        write_json(self.root / sf.SOURCE_FILES[1], studio)
        with self.assertRaisesRegex(sf.Invalid, "cannot recapture accepted overlays"):
            sf.reconstruct(self.root)
        for value in (None, 1, ["file"], {"path": "file"}):
            with self.subTest(value=value), self.assertRaisesRegex(sf.Invalid, "must be a string"):
                sf.relative(value)

    def test_restore_refuses_tampering_traversal_links_and_existing_destinations(self):
        save = self.base / "snapshot"
        sf.backup(self.root, self.db, save)
        existing = self.base / "existing"
        existing.mkdir()
        with self.assertRaisesRegex(sf.Invalid, "new independent"):
            sf.restore(save, existing)
        file = save / "studio-state/notes/base.json"
        original = file.read_bytes()
        file.write_bytes(original + b" ")
        with self.assertRaisesRegex(sf.Invalid, "integrity mismatch"):
            sf.restore(save, self.base / "tampered")
        file.write_bytes(original)
        manifest_path = save / "manifest.json"
        manifest = sf.read_json(manifest_path)
        broken = copy.deepcopy(manifest)
        broken["files"][0]["path"] = "../escape"
        write_json(manifest_path, broken)
        with self.assertRaisesRegex(sf.Invalid, "unsafe relative"):
            sf.restore(save, self.base / "traversal")
        write_json(manifest_path, manifest)
        file.unlink()
        file.symlink_to(self.db / "notes/base.json")
        with self.assertRaisesRegex(sf.Invalid, "symlink"):
            sf.restore(save, self.base / "linked")
        self.assertFalse((self.base / "linked").exists())


class SharedFingerprintTests(unittest.TestCase):
    def test_python_source_and_script_consumers_share_vectors_and_read_v1(self):
        vectors = sf.read_json(ROOT / "tests/fixtures/source-fingerprint-vectors.json")["vectors"]
        for vector in vectors:
            self.assertEqual(fp.source_fingerprint(vector["source"]), vector["v2"])
            self.assertEqual(scripts.source_fingerprint(vector["source"]), vector["v2"])
            self.assertEqual(scripts.source_fingerprint_v1(vector["source"]), vector["v1"])
            self.assertEqual(fp.source_binding(vector["source"])["sourceFingerprint"], vector["v2"])
        self.assertEqual(vectors[0]["v1"], vectors[2]["v1"])
        self.assertNotEqual(vectors[0]["v2"], vectors[2]["v2"])
        self.assertEqual(vectors[0]["v2"], vectors[1]["v2"])


if __name__ == "__main__":
    unittest.main()
