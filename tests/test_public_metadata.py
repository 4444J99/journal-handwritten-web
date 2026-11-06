"""Public navigation metadata must not enumerate withheld pages or blocks."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_public import filter_reader_metadata
from build_public import build
from script_realizations import source_snapshot
from source_fingerprint import source_binding


class MetadataFiltering(unittest.TestCase):
    pages = [{"id": "page-a", "B": [{}, {}]}, {"id": "page-b", "B": [{}]},
             {"id": "page-hidden", "B": [{}]}]
    html = '''const PAL = [
      {id:"comparison",witnesses:[[["page-a",[0]]],[["page-a",[1]]],[["page-hidden","all"]]]},
      {id:"whole",witnesses:[[["page-a","all"]],[["page-b","all"]]]}
    ];
    const HF = ["page-a","page-hidden"];'''

    def parse(self, value, name):
        return json.loads(re.search(r"const " + name + r" = (.*?);", value, re.S).group(1))

    def test_exact_selected_blocks_drop_hidden_witness_and_empty_comparisons(self):
        out = filter_reader_metadata(self.html, self.pages, {("page-a", 0), ("page-b", 0)})
        self.assertEqual(self.parse(out, "PAL"), [])
        self.assertEqual(self.parse(out, "HF"), [])
        self.assertNotIn("page-hidden", out)

    def test_two_complete_selected_witnesses_remain_without_hidden_metadata(self):
        out = filter_reader_metadata(self.html, self.pages, {("page-a", 0), ("page-a", 1)})
        pal = self.parse(out, "PAL")
        self.assertEqual([p["id"] for p in pal], ["comparison"])
        self.assertEqual(len(pal[0]["witnesses"]), 2)
        self.assertEqual(self.parse(out, "HF"), ["page-a"])
        self.assertNotIn("page-hidden", out)
        self.assertEqual(filter_reader_metadata(out, self.pages, {("page-a", 0), ("page-a", 1)}), out)

    def test_unrecognised_executable_literal_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Unsupported reader metadata"):
            filter_reader_metadata('const PAL = [getPrivatePages()];', self.pages, set())

    def test_source_template_is_filtered_for_single_real_piece(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "site/data/j.json").read_text())
        source = (root / "site/index.html").read_text()
        out = filter_reader_metadata(source, data["pages"], {("diary1", b) for b in range(6)})
        self.assertEqual(self.parse(out, "PAL"), [])
        self.assertEqual(self.parse(out, "HF"), [])
        self.assertNotIn('"diary53a"', out)

    def test_filtered_output_binds_only_exact_selected_effective_readings(self):
        root = Path(__file__).resolve().parents[1]
        original = json.loads((root / "site/data/j.json").read_text())
        piece = next(p for p in original["pieces"] if p["id"] == "p001")
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "output"
            build(out, ["p001"], site=root / "site", select={"p001": [0]},
                  corrections={("diary1", 0, 0): "synthetic technical fixture"}, rename_fonts=False)
            data = json.loads((out / "data/j.json").read_text())
            version = piece["V"][0]["id"]
            expected = source_binding(source_snapshot(root, "p001", version,
                correction_values={"diary1-0-0": "synthetic technical fixture"}))
            self.assertEqual(data["sourceBindings"], {f"p001/{version}": expected})
            self.assertNotEqual(expected, original["sourceBindings"][f"p001/{version}"])
            self.assertEqual(data["pages"][0]["B"][0]["L"][0], "synthetic technical fixture")
            self.assertEqual(data["sourceAnchors"]["diary1-2-3"], {"status": "unavailable"})
            self.assertNotIn("acceptedReadings", data)
            self.assertTrue(all(key.startswith("diary1-") for key in data["sourceAnchors"]))
            build(out, ["p001"], site=root / "site", select={"p001": [1]}, rename_fonts=False)
            data = json.loads((out / "data/j.json").read_text())
            for lid, value in original["acceptedReadings"].items():
                pg, bi, li = lid.rsplit("-", 2)
                if pg == "diary62a":
                    page = next(p for p in data["pages"] if p["id"] == pg)
                    self.assertEqual(page["B"][int(bi)]["L"][int(li)], value)

    def test_staged_photo_refusal_preserves_existing_output(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "site/data/j.json").read_text())
        next(p for p in data["pages"] if p["id"] == "diary1")["a"] = None
        with tempfile.TemporaryDirectory() as temp:
            site, out = Path(temp) / "site", Path(temp) / "output"
            (site / "data").mkdir(parents=True); out.mkdir()
            (site / "data/j.json").write_text(json.dumps(data))
            (out / "sentinel").write_text("preserve prior output")
            with self.assertRaisesRegex(SystemExit, "untranscribed or has no verified atlas"):
                build(out, ["p001"], site=site, select={"p001": [0]}, rename_fonts=False)
            self.assertEqual((out / "sentinel").read_text(), "preserve prior output")
            piece = next(p for p in data["pieces"] if p["id"] == "p001")
            # Actual ingest appends V without changing the established st/top.
            piece["V"].append({"id": "p001-fixture-stage", "P": [["diary1", [0]]],
                               "sourceStatus": "staged-untranscribed"})
            (site / "data/j.json").write_text(json.dumps(data))
            with self.assertRaisesRegex(SystemExit, "staged-untranscribed"):
                build(out, ["p001"], site=site, select={"p001": [len(piece["V"]) - 1]}, rename_fonts=False)
            self.assertEqual((out / "sentinel").read_text(), "preserve prior output")


if __name__ == "__main__":
    unittest.main()
