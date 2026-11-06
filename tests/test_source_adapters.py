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
from test_script_realizations import envelope, latest, reseal


class CurrentSourceAdapters(unittest.TestCase):
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
