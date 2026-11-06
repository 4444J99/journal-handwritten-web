"""Release-preparation contract checks against preserved data, never a live DB."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prepare_release_packet as packet
import post_poem as posting
import build_public


class ExposureContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = posting.Source(ROOT)
        cls.db = packet.load_inspection_db(ROOT, ROOT / "exports/studio-db-2026-11-05")

    def test_default_candidate_withholds_the_second_version_and_neighbour(self):
        result = packet.exposure_map(self.src, {"p001": [0]})
        self.assertEqual([p["page_id"] for p in result["pages"]], ["diary1"])
        self.assertEqual(result["withheld_blocks_visible"], [])
        self.assertEqual(result["selection"], {"p001": ["p001-diary1-0"]})

    def test_other_version_exposes_neighbour_even_when_transcript_is_empty(self):
        result = packet.exposure_map(self.src, {"p001": [0, 1]})
        exposed = result["withheld_blocks_visible"]
        self.assertEqual([(b["page_id"], b["block"]) for b in exposed], [("diary62a", 3), ("diary62a", 4)])
        self.assertEqual({x["piece_id"] for b in exposed for x in b["occupants"]}, {"p126"})
        self.assertTrue(all(not b["selected_text"] for b in exposed))

    def test_unselected_versions_of_same_piece_are_counted_as_exposure(self):
        result = packet.exposure_map(self.src, {"p002": [1]})
        exposed = {b["block"]: b for b in result["withheld_blocks_visible"]}
        self.assertTrue({0, 1, 4}.issubset(exposed))
        self.assertEqual(exposed[0]["occupants"][0]["piece_id"], "p002")
        self.assertFalse(exposed[0]["occupants"][0]["selected_version"])
        self.assertEqual(exposed[1]["type"], "quotation")

    def test_queue_retains_all_source_uncertainty_and_visibility_flags(self):
        queue = packet.author_queue(self.src, self.db)
        self.assertEqual(len({r["id"] for r in queue}), len(queue))
        self.assertEqual([r["page_sequence"] for r in queue], sorted(r["page_sequence"] for r in queue))
        expected = [(p["id"], note) for p in self.src.review["pages"] for note in p.get("uncertain", [])]
        actual = [(r["pages"][0], r["recorded_note"]) for r in queue if r["category"] == "uncertain-reading"]
        self.assertCountEqual(actual, expected)
        self.assertEqual({r["id"] for r in queue if r["category"] == "flagged-visibility"},
                         {f["key"] for f in self.src.review["flagged"]})
        self.assertEqual(sum(r["category"] == "possible-pair" for r in queue), 2)

    def test_output_cannot_overwrite_inputs_or_prior_packet(self):
        with self.assertRaisesRegex(ValueError, "overlaps source"):
            packet.prepare(ROOT, ROOT / "exports/studio-db-2026-11-05", "p001", ROOT / "site/never-create-this-packet")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "new directory"):
                packet.prepare(ROOT, ROOT / "exports/studio-db-2026-11-05", "p001", Path(tmp))


def fonts_available():
    py = build_public.font_python()
    if not os.path.isfile(py):
        return False
    import subprocess
    return subprocess.run([py, "-c", "import fontTools.ttLib.woff2; assert fontTools.ttLib.woff2.haveBrotli"],
                          capture_output=True).returncode == 0


@unittest.skipUnless(fonts_available(), "Set VERSFORMS_FONT_PYTHON to Python with fontTools and brotli")
class PacketDryRun(unittest.TestCase):
    def test_actual_gates_exclusion_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = packet.prepare(ROOT, ROOT / "exports/studio-db-2026-11-05", "p001", Path(tmp) / "one")
            second = packet.prepare(ROOT, ROOT / "exports/studio-db-2026-11-05", "p001", Path(tmp) / "two")
            self.assertEqual(first["actual_gated_dry_run"]["exit_code"], 3)
            self.assertFalse(first["gates"]["series"]["pass"])
            self.assertTrue(first["gates"]["all_versions_reviewed"]["pass"])
            self.assertFalse(first["gates"]["filed_or_registered_status"]["pass"])
            self.assertFalse(first["release_clearance"])
            self.assertTrue(first["inputs_unchanged"])
            self.assertTrue(first["preview"]["content_exclusion_pass"])
            self.assertFalse(first["preview"]["metadata_exclusion_pass"])
            self.assertFalse(first["preview"]["technical_exclusion_pass"])
            self.assertIn("diary53a", first["preview"]["engine_metadata_exposure"]["withheld_page_ids"])
            self.assertEqual(first["database_documents"]["release"], 0)
            self.assertEqual(first["preview"]["files"], second["preview"]["files"])
            self.assertEqual(len(first["preview"]["files"]), 8)
            self.assertEqual(first["preview"]["review_counts_for_selected_versions"]["confirmed"], 22)
            self.assertEqual(first["preview"]["review_counts_for_selected_versions"]["corrected"], 0)
            self.assertEqual(first["preview"]["corrected_lines_on_withheld_versions"], 5)
            output = json.loads((Path(tmp) / "one/preview/data/j.json").read_text())
            self.assertEqual([p["id"] for p in output["pieces"]], ["p001"])
            self.assertEqual([v["id"] for v in output["pieces"][0]["V"]], ["p001-diary1-0"])
            self.assertEqual([p["id"] for p in output["pages"]], ["diary1"])
            comparison = json.loads((Path(tmp) / "one/comparison-exposure.json").read_text())
            self.assertEqual(comparison["review_counts_for_selected_versions"]["confirmed"], 33)
            self.assertEqual(comparison["review_counts_for_selected_versions"]["corrected"], 5)
            self.assertFalse(comparison["technical_exclusion_pass"])
            self.assertFalse(comparison["release_clearance"])

    def test_stale_review_original_refuses_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "db"
            shutil.copytree(ROOT / "exports/studio-db-2026-11-05", db)
            line = db / "reviews/diary1-0-0.json"
            doc = json.loads(line.read_text()); doc["original"] = "fixture: stale review input"
            line.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, "Stale review originals"):
                packet.prepare(ROOT, db, "p001", Path(tmp) / "out")
            self.assertFalse((Path(tmp) / "out/preview").exists())


if __name__ == "__main__":
    unittest.main()
