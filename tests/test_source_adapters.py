"""Fresh v2 bindings across private output adapters; synthetic evidence only."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tests")]
import source_fingerprint as sf
import script_realizations as scripts
import release_contract as rc
import release_fixtures as rf
import source_regions as regions
from audio_build import render as audio
from test_script_realizations import envelope, latest, reseal


class CurrentSourceAdapters(unittest.TestCase):
    def test_region_and_audio_adapters_consume_all_shared_v2_vectors(self):
        vectors = json.loads((ROOT / "tests/fixtures/source-fingerprint-vectors.json").read_text())["vectors"]
        for vector in vectors:
            with self.subTest(vector=vector["name"]):
                source = vector["source"]
                expected = sf.source_binding(source)
                atom = {"piece_id": source["pieceId"], "version_id": source["versionId"], "page_id": "fixture-page",
                        "source_ids": {"line_id": source["lines"][0]["lineId"]},
                        "lineage": {"source_line_ids": [l["lineId"] for l in source["lines"]]}}
                self.assertEqual(regions.current_source_bindings({"atoms": [atom]}, snapshots=[source]), [expected])
                request = {"id": "test-audio", "text": "\n".join(l["text"] for l in source["lines"])}
                bound = audio.bind_request_source(request, source, [l["lineId"] for l in source["lines"]])
                self.assertEqual(audio.current_source_bindings({"requests": [bound]}, snapshots=[source]), [expected])
                self.assertEqual(expected["sourceFingerprint"], vector["v2"])
                old = copy.deepcopy(source)
                old["versionFingerprint"] = vector["v1"]
                with self.assertRaisesRegex(ValueError, "v2 rebind"):
                    regions.current_source_bindings({"atoms": [atom]}, snapshots=[old])
                with self.assertRaisesRegex(ValueError, "v2 rebind"):
                    audio.current_source_bindings({"requests": [bound]}, snapshots=[old])

    def test_explicit_import_line_ids_and_source_changes_are_not_retargeted(self):
        source = {"pieceId": "test-piece", "versionId": "test-version", "members": [["test-photo", [0]]],
                  "lines": [{"lineId": "explicit-import-line", "text": "TECHNICAL TEST", "blockType": "text", "breakBefore": False}]}
        request = audio.bind_request_source({"text": "TECHNICAL TEST"}, source, ["explicit-import-line"])
        for name in ("text", "stanza", "membership"):
            changed = copy.deepcopy(source)
            if name == "text": changed["lines"][0]["text"] += " CHANGED"
            if name == "stanza": changed["lines"][0]["breakBefore"] = True
            if name == "membership": changed["members"][0][1] = [1]
            with self.subTest(name=name), self.assertRaises(ValueError):
                audio.current_source_bindings({"requests": [request]}, snapshots=[changed])
        with self.assertRaisesRegex(ValueError, "exact current version"):
            audio.bind_request_source({"text": "TECHNICAL TEST"}, source, ["test-photo-0-0"])
        atom = {"piece_id": "test-piece", "version_id": "test-version", "source_ids": {"line_id": "test-photo-0-0"}}
        with self.assertRaisesRegex(ValueError, "exact current version"):
            regions.current_source_bindings({"atoms": [atom]}, snapshots=[source])
        untranscribed = copy.deepcopy(source)
        untranscribed["lines"][0].update(text=None, transcriptionStatus="untranscribed")
        with self.assertRaisesRegex(ValueError, "transcribed"):
            sf.source_binding(untranscribed)

    def test_bound_audio_render_rechecks_current_source_and_retains_fixture_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "source"
            source_data = {"pieces": [{"id": "test-piece", "V": [{"id": "test-version", "P": [["test-photo", [0]]]}]}]}
            review_data = {"pages": [{"id": "test-photo", "blocks": [{"t": "text", "lines": [{"id": "explicit-import-line", "tx": "calibration"}]}]}]}
            for name, value in (("site/data/j.json", source_data), ("studio/data/review.json", review_data)):
                path = repo / name
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(value))
            source = scripts.source_snapshot(repo, "test-piece", "test-version")
            audio.fixture(root / "session")
            path = root / "session/session.json"
            manifest = audio.json_read(path)
            manifest["requests"] = [audio.bind_request_source(manifest["requests"][0], source, ["explicit-import-line"])]
            path.write_bytes(audio.json_bytes(manifest))
            audio.run(path, root / "listen", source_repo=repo)
            receipt = audio.json_read(root / "listen/receipt.json")
            self.assertEqual(receipt["source_bindings"], [sf.source_binding(source)])
            self.assertEqual(receipt["source_fingerprint_version"], 2)
            self.assertTrue(receipt["fixture"])
            self.assertEqual(receipt["privacy"]["rendered_release"], "undecided")
            review_data["acceptedReviews"] = {"explicit-import-line": {"status": "corrected", "original": "calibration", "text": "CHANGED TECHNICAL TEST"}}
            (repo / "studio/data/review.json").write_text(json.dumps(review_data))
            with self.assertRaises(audio.PilotError) as error:
                audio.validate_manifest(path, source_repo=repo)
            self.assertEqual(error.exception.code, "source_binding_stale")

    def test_v1_history_remains_readable_but_cannot_be_the_current_public_source(self):
        value = envelope("TECHNICAL TEST LINE ONE")
        revision = latest(value)
        revision["source"]["members"][0][1].append(1)
        revision["source"]["lines"].append({"lineId": "line-test-two", "text": "TECHNICAL TEST LINE TWO",
            "originalText": "TECHNICAL TEST LINE TWO", "blockType": "text", "breakBefore": True})
        revision["source"]["versionFingerprint"] = sf.source_fingerprint_v1(revision["source"])
        revision["lines"].append({"id": "test-line-two", "sourceLineIds": ["line-test-two"],
                                  "text": "TECHNICAL TEST LINE TWO", "breakBefore": True})
        revision.update(fixture=False, visibility="public-proposed")
        revision["method"]["kind"] = "human-supplied"
        revision["authors"] = [{"id": "test-source", "role": "source-author", "evidence": "synthetic-only"},
                               {"id": "test-realizer", "role": "realizer", "evidence": "synthetic-only"}]
        revision["glyphAssets"][0]["visibility"] = "public-proposed"
        reseal(value)
        scripts.validate(value)  # History is retained; only current use is refused.
        revision = latest(value)
        current = copy.deepcopy(revision["source"])
        current["lines"][1]["breakBefore"] = False
        self.assertEqual(sf.source_fingerprint_v1(current), current["versionFingerprint"])
        with self.assertRaisesRegex(ValueError, "v2 rebind"):
            sf.source_binding(current)
        source = {"pieceId": "p-test", "versionId": "v-test", "sourceFingerprint": current["versionFingerprint"]}
        component = {"kind": "realization", "id": value["realizations"][0]["id"], **source,
                     "revisionDigest": revision["digest"], "fixture": False, "path": "realization.json", "sha256": rc.digest(value)}
        context = rf.context([source], [component])
        glyph = revision["glyphAssets"][0]
        context["manifest"]["files"].append({"path": glyph["path"], "bytes": 1, "sha256": glyph["sha256"]})
        context["manifest"]["manifestDigest"] = rc.digest({k: v for k, v in context["manifest"].items() if k != "manifestDigest"})
        context["clearance"] = rf.clearance(context["manifest"])
        output = scripts.projection(value, {("p-test", "v-test"): current},
            {"p-test": {"pool": "series", "visibility": "public"}}, audience="public", release_context=context)
        self.assertEqual(output["realizations"], [])

    def test_explicit_output_corrections_exclude_unselected_embedded_readings(self):
        default = scripts.source_snapshot(ROOT, "p001", "p001-diary62a-0")
        raw = scripts.source_snapshot(ROOT, "p001", "p001-diary62a-0", correction_values={})
        self.assertNotEqual(default["versionFingerprint"], raw["versionFingerprint"])
        self.assertTrue(all(line["text"] == line["originalText"] for line in raw["lines"]))
        selected = {line["lineId"]: line["text"] for line in default["lines"] if line["text"] != line["originalText"]}
        restored = scripts.source_snapshot(ROOT, "p001", "p001-diary62a-0", correction_values=selected)
        self.assertEqual(restored["versionFingerprint"], default["versionFingerprint"])
        for invalid in ({"missing-line": "TECHNICAL TEST"}, {"diary1-0-0": None}, {"diary2-1-0": "TECHNICAL TEST"}):
            with self.subTest(invalid=invalid), self.assertRaises(scripts.Invalid):
                scripts.source_snapshot(ROOT, "p001", "p001-diary1-0", correction_values=invalid)

    def test_output_binding_refuses_reader_original_drift_and_stale_exported_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            for name in ("site/data/j.json", "studio/data/review.json"):
                path = repo / name
                path.parent.mkdir(parents=True)
                path.write_bytes((ROOT / name).read_bytes())
            path = repo / "site/data/j.json"
            reader = json.loads(path.read_text())
            reader["pages"][0]["B"][0]["L"][0] += " TECHNICAL TEST DRIFT"
            path.write_text(json.dumps(reader))
            with self.assertRaisesRegex(scripts.Invalid, "raw originals differ"):
                scripts.source_snapshot(repo, "p001", "p001-diary1-0", correction_values={})
            path.write_bytes((ROOT / "site/data/j.json").read_bytes())
            folder = repo / "db/reviews"
            folder.mkdir(parents=True)
            (folder / "diary1-0-0.json").write_text(json.dumps({"status": "corrected", "original": "STALE TECHNICAL TEST", "text": "The walls"}))
            with self.assertRaisesRegex(scripts.Invalid, "stale correction"):
                scripts.source_snapshot(repo, "p001", "p001-diary1-0", repo / "db", correction_values={})


if __name__ == "__main__":
    unittest.main()
