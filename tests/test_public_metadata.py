"""Public navigation metadata must not enumerate withheld pages or blocks."""
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from build_public import filter_reader_metadata
from build_public import build, rename_embedded_fonts, run_font_tool, DATA_URI_RE, is_font
import base64
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
            self.assertNotIn("diary1-2-3", data.get("sourceAnchors", {}))
            self.assertNotIn("acceptedReadings", data)
            self.assertTrue(all(key.startswith("diary1-") for key in data.get("sourceAnchors", {})))
            for module in ("reader-features.js", "reader-packages.js"):
                self.assertEqual((out / module).read_bytes(), (root / "site" / module).read_bytes())
            build(out, ["p001"], site=root / "site", select={"p001": [1]}, rename_fonts=False)
            data = json.loads((out / "data/j.json").read_text())
            for lid, value in original["acceptedReadings"].items():
                pg, bi, li = lid.rsplit("-", 2)
                if pg == "diary62a":
                    page = next(p for p in data["pages"] if p["id"] == pg)
                    self.assertEqual(page["B"][int(bi)]["L"][int(li)], value)

    def test_public_build_omits_global_transcription_claim(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "public"
            build(out, ["p001"], site=root / "site", select={"p001": [0]}, rename_fonts=False)
            html = (out / "index.html").read_text()
            self.assertNotIn("Machine transcription (", html)
            self.assertNotIn("not yet checked", html)
            self.assertNotIn('"diary53a"', html)
            self.assertNotIn('"diary21a"', html)

    def test_public_font_blanks_journal_provenance_and_preserves_glyphs(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "site/index.html").read_text()
        output, reports = rename_embedded_fonts(source)
        def fonts(html):
            return [base64.b64decode(m[2]) for m in DATA_URI_RE.finditer(html)
                    if is_font(m[1], base64.b64decode(m[2]))]
        for original, public in zip(fonts(source), fonts(output)):
            before, after = run_font_tool("describe", original), run_font_tool("describe", public)
            for key, value in after["name_records"].items():
                if key.split("/")[0] in ("0", "10"):
                    self.assertEqual(value, "")
            for key in ("glyph_order", "cmap", "hmtx", "tables", "head_modified"):
                self.assertEqual(before[key], after[key])
        self.assertEqual(rename_embedded_fonts(output)[0], output)

    def test_public_font_scrub_preserves_license_text_and_url(self):
        import subprocess
        from build_public import font_python, FONT_TOOL
        root = Path(__file__).resolve().parents[1]
        html = (root / "site/index.html").read_text()
        raw = next(base64.b64decode(m[2]) for m in DATA_URI_RE.finditer(html)
                   if is_font(m[1], base64.b64decode(m[2])))
        script = """import sys,io
from fontTools.ttLib import TTFont
f=TTFont(io.BytesIO(sys.stdin.buffer.read()),recalcTimestamp=False)
f['name'].setName('License holder ETCETER4',13,3,1,1033)
f['name'].setName('https://example.invalid/ETCETER4/license',14,3,1,1033)
b=io.BytesIO();f.save(b);sys.stdout.buffer.write(b.getvalue())
"""
        seeded = subprocess.run([font_python(), "-c", script], input=raw, capture_output=True, check=True).stdout
        from build_public import PUBLIC_FONT_FAMILY, PUBLIC_FONT_FULL, PUBLIC_FONT_PS
        result = run_font_tool("rename", seeded, "--family", PUBLIC_FONT_FAMILY,
            "--full", PUBLIC_FONT_FULL, "--postscript", PUBLIC_FONT_PS, "--strip-journal-metadata")
        names = run_font_tool("describe", base64.b64decode(result["font_b64"]))["name_records"]
        self.assertEqual(names["13/3/1/1033"], "License holder ETCETER4")
        self.assertEqual(names["14/3/1/1033"], "https://example.invalid/ETCETER4/license")

    def test_diary1_block2_has_four_correct_ordered_regions(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "site/data/j.json").read_text())
        page = next(p for p in data["pages"] if p["id"] == "diary1")
        rows = [r for r in page["x"] if r[0] == 2]
        self.assertEqual([r[1] for r in rows], [0, 1, 2, 3])
        self.assertLess(rows[1][3], .40)  # second ink line starts near y=610/1600
        self.assertGreater(rows[2][3], .41)
        self.assertGreater(rows[3][3], .45)
        self.assertLess(rows[3][4], .30)  # stone. is short, not the stepping line
        self.assertNotIn("diary1-2-3", data.get("sourceAnchors", {}))

    def test_missing_transitive_reader_module_preserves_existing_output(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            site, out = Path(temp) / "site", Path(temp) / "output"
            (site / "data").mkdir(parents=True); out.mkdir()
            for relative in ("data/j.json", "index.html", "reader-features.js"):
                (site / relative).write_bytes((root / "site" / relative).read_bytes())
            (out / "sentinel").write_text("preserve prior output")
            with self.assertRaisesRegex(FileNotFoundError, "reader-packages.js"):
                build(out, ["p001"], site=site, select={"p001": [0]}, rename_fonts=False)
            self.assertEqual((out / "sentinel").read_text(), "preserve prior output")

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
