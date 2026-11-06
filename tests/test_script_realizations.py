"""T10 identity, lossless storage, Unicode, and exclusion regressions.

All invented strings here are labeled technical test data, not poems.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import script_realizations as sr
from make_test_font import build


def source(text="A B C"):
    value = {"pieceId": "p-test", "versionId": "v-test", "members": [["page-test", [0]]],
             "lines": [{"lineId": "line-test", "text": text, "originalText": text,
                        "blockType": "text", "breakBefore": False}], "versionFingerprint": "",
             "provenance": {"repository": "technical-fixture", "contract": "T05-proposed-fingerprint-v1",
                 "files": [{"path": "technical-source.json", "sha256": "sha256:" + "0" * 64}],
                 "reviewRecords": [], "readingStatus": "technical-fixture"}}
    value["versionFingerprint"] = sr.source_fingerprint(value)
    return value


def envelope(text="A B C"):
    asset = {"id": "test-font", "kind": "font", "path": "assets/test.otf", "sha256": "sha256:" + "1" * 64,
             "visibility": "private", "author": "technical-fixture", "sourceLocator": "tests/make_test_font.py"}
    return sr.fixture(source(text), asset)


def latest(value):
    return value["realizations"][0]["revisions"][-1]


def reseal(value):
    value["realizations"][0]["revisions"][-1] = sr.seal(latest(value))
    return value


def append(value, change, **updates):
    result = copy.deepcopy(value)
    old = latest(result)
    new = copy.deepcopy(old)
    new.update(id="revision-" + str(len(result["realizations"][0]["revisions"]) + 1),
               parent=old["digest"], change=change, at="2026-11-05T23:01:00Z", **updates)
    result["realizations"][0]["revisions"].append(sr.seal(new))
    return result


def project(value, *, policy=None, current=None, audience="private"):
    return sr.projection(value, {("p-test", "v-test"): current or latest(value)["source"]},
                         {"p-test": policy or {"pool": "unsorted", "visibility": "private"}}, audience=audience)


class StorageAndIdentity(unittest.TestCase):
    def test_roundtrip_preserves_nfd_scalar_sequences_and_history(self):
        value = envelope("A\u0301 C")
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp) / "store"
            self.assertEqual(sr.restore(value, store)["added"], 1)
            self.assertEqual(sr.pack(store), value)
            self.assertEqual(sr.restore(value, store)["added"], 0)
            self.assertEqual(latest(sr.pack(store))["lines"][0]["text"], "A\u0301 C")
            self.assertNotEqual(latest(sr.pack(store))["lines"][0]["text"], "Á C")

    def test_history_collision_and_fork_refused_before_writes(self):
        value = envelope()
        extended = append(value, "script-change", language="und", script="Grek")
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp) / "store"
            sr.restore(extended, store)
            before = {p.name: p.read_bytes() for p in store.iterdir()}
            fork = append(value, "script-change", language="und", script="Cyrl")
            fork["realizations"][0]["revisions"][-1]["id"] = "different-id"
            reseal(fork)
            with self.assertRaises(sr.Invalid):
                sr.restore(fork, store)
            self.assertEqual(before, {p.name: p.read_bytes() for p in store.iterdir()})

    def test_script_change_does_not_modify_source_or_other_editorial_data(self):
        value = envelope()
        new = append(value, "script-change", language="und", script="Grek")
        sr.validate(new)  # metadata-only test, not a Greek poem or rendering claim
        self.assertEqual(latest(new)["source"], latest(value)["source"])
        self.assertEqual(new["realizations"][0]["versionId"], "v-test")
        self.assertEqual(value["realizations"][0]["revisions"], new["realizations"][0]["revisions"][:1])

    def test_source_edit_invalidates_until_explicit_distinct_source_rebind(self):
        value = envelope()
        changed_source = source("A C")
        out = project(value, current=changed_source)
        self.assertEqual(out["realizations"], [])
        self.assertIn("source-changed", out["excluded"][0]["reasons"])
        new = append(value, "source-rebind", source=changed_source,
                     lines=[{"id": "line-r2", "sourceLineIds": ["line-test"], "text": "A C", "breakBefore": False}])
        sr.validate(new)
        self.assertEqual(len(project(new, current=changed_source)["realizations"]), 1)
        bad = copy.deepcopy(new)
        latest(bad)["script"] = "Grek"
        reseal(bad)
        with self.assertRaisesRegex(sr.Invalid, "distinct revisions"):
            sr.validate(bad)

    def test_changing_editorial_version_requires_new_realization(self):
        value = envelope()
        latest(value)["source"]["versionId"] = "other-version"
        latest(value)["source"]["versionFingerprint"] = sr.source_fingerprint(latest(value)["source"])
        reseal(value)
        with self.assertRaises(sr.Invalid):
            sr.validate(value)

    def test_line_anchor_is_not_a_display_coordinate(self):
        value = envelope()
        latest(value)["lines"][0]["sourceLineIds"] = ["not-in-source"]
        reseal(value)
        with self.assertRaises(sr.Invalid):
            sr.validate(value)

    def test_mode_and_authorship_do_not_silently_become_translation(self):
        value = envelope()
        latest(value)["mode"] = "translation"
        reseal(value)
        with self.assertRaises(sr.Invalid):
            sr.validate(value)
        latest(value)["method"]["kind"] = "human-supplied"
        latest(value)["fixture"] = False
        reseal(value)
        with self.assertRaisesRegex(sr.Invalid, "authorship"):
            sr.validate(value)

    def test_unknown_fields_duplicate_keys_and_bidi_controls_rejected(self):
        value = envelope()
        latest(value)["approveEverything"] = True
        with self.assertRaises(sr.Invalid):
            sr.validate(value)
        with self.assertRaises(sr.Invalid):
            envelope("A\u202eB")
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "bad.json"
            p.write_text('{"format":"one","format":"two"}')
            with self.assertRaises(sr.Invalid):
                sr.read_json(p)

    def test_script_change_and_visibility_change_are_classified(self):
        with self.assertRaises(sr.Invalid):
            sr.validate(append(envelope(), "realization-edit", script="Grek"))
        sr.validate(append(envelope(), "visibility-change", visibility="withheld"))
        with self.assertRaises(sr.Invalid):
            sr.validate(append(envelope(), "visibility-change", layout={"direction": "rtl", "writingMode": "horizontal-tb"}))

    def test_revised_glyph_bytes_require_a_new_immutable_path(self):
        value = envelope()
        assets = copy.deepcopy(latest(value)["glyphAssets"])
        assets[0]["sha256"] = "sha256:" + "2" * 64
        with self.assertRaisesRegex(sr.Invalid, "asset path reused"):
            sr.validate(append(value, "realization-edit", glyphAssets=assets))
        assets[0]["path"] = "assets/test-r2.otf"
        sr.validate(append(value, "realization-edit", glyphAssets=assets))


class ExclusionAndPreview(unittest.TestCase):
    def test_reserve_withheld_and_unknown_policy_excluded_before_projection(self):
        value = envelope()
        for policy in ({"pool": "reserve", "visibility": "private"},
                       {"pool": "series", "visibility": "withheld"},
                       {"pool": "Series", "visibility": "public"}):
            with self.subTest(policy=policy):
                self.assertEqual(project(value, policy=policy)["realizations"], [])
        for field in ("realization", "glyph"):
            edited = copy.deepcopy(value)
            if field == "glyph":
                latest(edited)["glyphAssets"][0]["visibility"] = "withheld"
            else:
                latest(edited)["visibility"] = "withheld"
            reseal(edited)
            self.assertEqual(project(edited)["realizations"], [])

    def test_public_proposed_label_cannot_authorize_output(self):
        value = envelope("PRIVATE TECHNICAL SENTINEL")
        latest(value)["visibility"] = "public-proposed"
        latest(value)["glyphAssets"][0]["visibility"] = "public-proposed"
        reseal(value)
        projected = project(value, audience="public", policy={"pool": "series", "visibility": "public"})
        self.assertEqual(projected["realizations"], [])
        self.assertNotIn("PRIVATE TECHNICAL SENTINEL", json.dumps(projected))
        self.assertNotIn("sourceLocator", json.dumps(projected))
        self.assertNotIn("p-test", json.dumps(projected))
        self.assertNotIn("t10-p001-latn-fixture", json.dumps(projected))
        self.assertNotIn("excluded", projected)

    def test_private_preview_escapes_html_and_keeps_combining_run_together(self):
        value = envelope('A\u0301 <script>alert(1)</script>')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "assets").mkdir()
            font = root / "assets" / "test.otf"
            font.write_bytes(build("Technical Fixture", "none"))
            latest(value)["glyphAssets"][0]["sha256"] = sr.file_hash(font)
            reseal(value)
            markup, report = sr.preview_html(project(value), root)
            self.assertIn('class="line fallback"', markup)
            self.assertIn('A\u0301 &lt;script&gt;', markup)
            self.assertNotIn('<script>', markup)
            self.assertEqual(report["lineCount"], 1)
            self.assertIn("U+0301", report["fallbackRuns"][0]["codepoints"])
            font.write_bytes(font.read_bytes() + b"changed")
            with self.assertRaisesRegex(sr.Invalid, "changed"):
                sr.preview_html(project(value), root)

    def test_private_artifacts_cannot_be_written_under_publishing_inputs(self):
        for path in (ROOT / "site" / "t10", ROOT / "studio" / "t10", ROOT / "release" / "t10",
                     ROOT / "docs" / ".." / "site" / "t10",
                     Path("/tmp/other-checkout/public/t10"), Path("/tmp/other-checkout/site/t10")):
            with self.assertRaises(sr.Invalid):
                sr.private_destination(path)

    def test_linked_store_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "target").mkdir()
            (root / "link").symlink_to(root / "target", target_is_directory=True)
            with self.assertRaises(sr.Invalid):
                sr.restore(envelope(), root / "link" / "store")

    def test_active_store_lock_refuses_a_second_writer_without_new_records(self):
        import fcntl
        import os
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp) / "store"
            store.mkdir()
            descriptor = os.open(store, os.O_RDONLY | os.O_DIRECTORY)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaisesRegex(sr.Invalid, "busy"):
                    sr.restore(envelope(), store)
                self.assertEqual(list(store.iterdir()), [])
            finally:
                os.close(descriptor)
            self.assertEqual(sr.restore(envelope(), store)["added"], 1)


class CurrentRepositoryContract(unittest.TestCase):
    def test_current_fixture_source_matches_t05_fingerprint_vector(self):
        # Known source vector at main 038d01f. Changes must update this evidence
        # deliberately, not silently migrate existing realization source hashes.
        current = sr.source_snapshot(ROOT, "p001", "p001-diary1-0", ROOT / "exports/studio-db-2026-11-05")
        self.assertEqual(current["versionFingerprint"], "sha256:5de0901485952e6ad279fce6ea102af4f830f2a4813e82842a90ebcc3d8d217a")
        self.assertEqual(len(current["lines"]), 22)
        self.assertEqual(sr.release_policy(ROOT, "p001", ROOT / "exports/studio-db-2026-11-05"), {"pool": "unsorted", "visibility": "private"})


if __name__ == "__main__":
    unittest.main()
