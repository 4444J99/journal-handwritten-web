"""Private glyph derivatives: provenance, scalar fidelity and rejection gates."""
from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import glyph_workflow as glyph
import script_realizations as realizations
from make_test_font import build


def sha(data):
    return hashlib.sha256(data).hexdigest()


class GlyphWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="glyph-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.capture = self.root / "capture.png"
        source = Image.new("RGB", (80, 40), "white")
        source.paste("black", (4, 4, 20, 30))
        source.save(self.capture)
        self.provenance = {
            "visibility": "private",
            "source": {"piece_id": "p001", "version_id": "p001-diary1-0",
                       "sha256": "a" * 64, "visibility": "public",
                       "collection": "series", "locator": "fixture:source-version"},
            "authorship": {"actor": "type engineer", "role": "technical-fixture",
                           "evidence": "Synthetic pixels for validation; no author acceptance."},
        }
        self.manifest = {
            "schema_version": 1, "id": "capture-fixture", **copy.deepcopy(self.provenance),
            "language": "en", "script": "Latn", "direction": "ltr",
            "capture": {"path": "capture.png", "sha256": sha(self.capture.read_bytes()),
                        "width": 80, "height": 40, "source_id": "synthetic-test",
                        "locator": "fixture:synthetic-test-pixels"},
            "glyphs": [{"id": "g001", "sequence": "A\u0301", "scalars": ["U+0041", "U+0301"],
                        "rect": [0, 0, 30, 40], "visibility": "private"}],
        }
        self.manifest_path = self.root / "input.json"
        self.counter = 0

    def write_manifest(self, manifest=None):
        self.manifest_path.write_text(json.dumps(manifest or self.manifest, ensure_ascii=False), encoding="utf-8")
        return self.manifest_path

    def source_export(self):
        """A real minimal repository/export, parsed by the shared source resolver."""
        repo = self.root / "checkout"
        db = self.root / "export"
        documents = {
            "site/data/j.json": {
                "pieces": [{"id": "p001", "V": [{"id": "p001-diary1-0", "P": [["page1", [0]]]}]}],
                "pages": [{"id": "page1"}],
            },
            "studio/data/review.json": {
                "items": [{"id": "p001"}],
                "pages": [{"id": "page1", "blocks": [{"t": "text", "lines": [{"id": "line1", "tx": "A"}]}]}],
            },
            "release/public.json": {"pieces": []},
        }
        for name, value in documents.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value))
        (db / "release").mkdir(parents=True)
        (db / "reviews").mkdir()
        provenance = copy.deepcopy(self.provenance)
        provenance["source"].update(visibility="private", collection="unsorted")
        source = realizations.source_snapshot(repo, "p001", "p001-diary1-0", db)
        provenance["source"]["sha256"] = source["versionFingerprint"].removeprefix("sha256:")
        return repo, db, provenance

    def rejected(self, manifest=None, message=None):
        self.counter += 1
        output = self.root / f"uncreated-parent-{self.counter}" / "bundle"
        with self.assertRaises(glyph.ValidationError, msg=message):
            glyph.import_capture(self.write_manifest(manifest), output)
        self.assertFalse(output.parent.exists(), "invalid import created output directories")

    def test_capture_preserves_provenance_scalars_pixels_and_is_deterministic(self):
        original = self.capture.read_bytes()
        path = self.write_manifest()
        first = glyph.import_capture(path, self.root / "first")
        second = glyph.import_capture(path, self.root / "second")
        self.assertEqual(self.capture.read_bytes(), original)
        self.assertEqual(first["source"], self.provenance["source"])
        self.assertEqual(first["authorship"], self.provenance["authorship"])
        self.assertEqual(first["review_status"], "unreviewed-supplied-labels")
        self.assertEqual(first["glyphs"][0]["sequence"], "A\u0301")
        self.assertEqual(first["glyphs"][0]["source_sha256"], sha(original))
        self.assertEqual(first["glyphs"][0]["rect"], [0, 0, 30, 40])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        for filename in ("g001.png", "manifest.json", "preview.html"):
            self.assertEqual((self.root / "first" / filename).read_bytes(), (self.root / "second" / filename).read_bytes())
        with Image.open(self.root / "first/g001.png") as crop:
            self.assertEqual(crop.size, (30, 40))
            self.assertEqual(crop.getpixel((5, 5)), (0, 0, 0, 255))
        stored = (self.root / "first/manifest.json").read_bytes()
        self.assertEqual(sha(stored), first["manifest_sha256"])

    def test_supplied_labels_and_provenance_are_html_escaped(self):
        value = copy.deepcopy(self.manifest)
        value["glyphs"][0]["sequence"] = '<img src=x onerror="x">'
        value["glyphs"][0].pop("scalars")
        value["authorship"]["evidence"] = '<script>alert("label")</script>'
        result = glyph.import_capture(self.write_manifest(value), self.root / "escaped")
        preview = (self.root / "escaped/preview.html").read_text()
        self.assertNotIn('<img src=x', preview)
        self.assertNotIn('<script>', preview)
        self.assertIn('&lt;img src=x onerror=&quot;x&quot;&gt;', preview)
        self.assertIn('UNREVIEWED SUPPLIED LABELS', preview)
        self.assertEqual(result["authorship"]["evidence"], value["authorship"]["evidence"])

    def test_restricted_unknown_or_noncanonical_provenance_never_emits_derivatives(self):
        for visibility in ("withheld", "public", "public-proposed", None):
            value = copy.deepcopy(self.manifest)
            value["visibility"] = visibility
            self.rejected(value)
        for collection in ("reserve", "archive", "unknown", "Reserve", " reserve ", "Series", "series "):
            value = copy.deepcopy(self.manifest)
            value["source"]["collection"] = collection
            self.rejected(value)
        value = copy.deepcopy(self.manifest)
        value["source"]["visibility"] = "withheld"
        self.rejected(value)
        for visibility in ("withheld", "public", None):
            value = copy.deepcopy(self.manifest)
            value["glyphs"][0]["visibility"] = visibility
            self.rejected(value)
        self.assertTrue(self.capture.exists(), "source preservation is outside derivative gating")

    def test_invalid_hash_image_dimensions_geometry_and_sequence_are_atomic(self):
        changes = [
            ("capture", "sha256", "0" * 64), ("capture", "width", 79),
            ("capture", "width", True), ("capture", "height", 50_000_000),
            ("glyph", "rect", [0, 0, 0, 1]), ("glyph", "rect", [-1, 0, 1, 1]),
            ("glyph", "rect", [79, 0, 2, 1]), ("glyph", "rect", [0, 39, 1, 2]),
            ("glyph", "rect", [0, 0, 1.5, 1]), ("glyph", "rect", [False, 0, 1, 1]),
            ("glyph", "scalars", ["U+00C1"]), ("glyph", "sequence", "A\u202e"),
            ("glyph", "sequence", "\ud800"), ("glyph", "id", "../x"),
        ]
        for section, key, item in changes:
            with self.subTest(section=section, key=key, item=repr(item)):
                value = copy.deepcopy(self.manifest)
                target = value["glyphs"][0] if section == "glyph" else value[section]
                target[key] = item
                if item == "\ud800":
                    # Escaped surrogate JSON is legal to parse but not a Unicode scalar.
                    self.manifest_path.write_text(json.dumps(value), encoding="utf-8")
                    with self.assertRaises(glyph.ValidationError):
                        glyph.import_capture(self.manifest_path, self.root / "bad-surrogate")
                    self.assertFalse((self.root / "bad-surrogate").exists())
                else:
                    self.rejected(value)
        value = copy.deepcopy(self.manifest)
        value["glyphs"].append(copy.deepcopy(value["glyphs"][0]))
        self.rejected(value)
        self.capture.write_bytes(b"not PNG")
        value = copy.deepcopy(self.manifest)
        value["capture"]["sha256"] = sha(self.capture.read_bytes())
        self.rejected(value)

    def test_strict_json_rejects_duplicate_keys_nonfinite_values_and_boolean_schema(self):
        base = json.dumps(self.manifest)
        cases = [base.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')]
        cases += [base[:-1] + ', "ignored": ' + number + '}' for number in ("NaN", "Infinity", "-Infinity", "1e1000")]
        cases += [base.replace('"schema_version": 1', '"schema_version": true')]
        for index, raw in enumerate(cases):
            self.manifest_path.write_text(raw)
            out = self.root / f"strict-{index}"
            with self.assertRaises(glyph.ValidationError):
                glyph.import_capture(self.manifest_path, out)
            self.assertFalse(out.exists())

    def test_path_traversal_symlinks_release_paths_and_oversize_are_rejected(self):
        for path in ("../capture.png", str(self.capture), "..\\capture.png", "C:source.png"):
            value = copy.deepcopy(self.manifest)
            value["capture"]["path"] = path
            self.rejected(value)
        (self.root / "linked.png").symlink_to(self.capture)
        value = copy.deepcopy(self.manifest)
        value["capture"]["path"] = "linked.png"
        self.rejected(value)
        path = self.write_manifest()
        for part in ("site", "studio", "release", "releases", "dist", "public"):
            out = self.root / part / "bundle"
            with self.assertRaises(glyph.ValidationError):
                glyph.import_capture(path, out)
            self.assertFalse(out.parent.exists())
        with patch.object(glyph, "MAX_BYTES", 4):
            with self.assertRaises(glyph.ValidationError):
                glyph.inspect_font(self.capture)

    def test_sheet_keeps_nfc_nfd_distinct_three_repetitions_and_boundaries(self):
        result = glyph.make_sheet("A\u0301 Á A\u0301\n<", "Latn", "en", self.root / "sheet.html", provenance=self.provenance)
        self.assertEqual(result["sequences"], ["A\u0301", "Á", "<"])
        sheet = (self.root / "sheet.html").read_text()
        self.assertEqual(sheet.count('class="slot"'), 9)
        self.assertIn("U+0041 U+0301", sheet)
        self.assertIn("U+00C1", sheet)
        self.assertIn("&lt;", sheet)
        for text in ("\u0301", "A \u0301", "A\n\u0301", "A\u00a0\u0301", "A\t\u0301"):
            with self.assertRaises(glyph.ValidationError):
                glyph.make_sheet(text, "Latn", "en", self.root / "unwritten.html", provenance=self.provenance)
            self.assertFalse((self.root / "unwritten.html").exists())

    def test_font_audit_and_import_preserve_bytes_names_and_identify_fallback(self):
        font_path = self.root / "fixture.otf"
        data = build("Fixture Original Family", "none")
        font_path.write_bytes(data)
        audit = glyph.inspect_font(font_path)
        self.assertEqual(audit["sha256"], sha(data))
        self.assertEqual(audit["codepoints"], [32, 65, 66, 67])
        self.assertEqual(audit["glyph_count"], 6)
        self.assertFalse(audit["shaping"]["GPOS"]["present"])
        result = glyph.import_font(font_path, self.root / "font", provenance=self.provenance, text="A\u0301\nB")
        self.assertEqual((self.root / "font/source-font.otf").read_bytes(), data)
        self.assertEqual(result["audit"]["names"]["family"], "Fixture Original Family")
        self.assertEqual(result["fallback_scalars"], ["U+0301"])
        self.assertIn("font-family:ajp-scribbles", (self.root / "font/preview.html").read_text())
        self.assertEqual(font_path.read_bytes(), data)

    def test_font_and_sheet_share_source_exclusion_and_refuse_overwrite(self):
        restricted = copy.deepcopy(self.provenance)
        restricted["source"]["visibility"] = "withheld"
        with self.assertRaises(glyph.ValidationError):
            glyph.make_sheet("A", "Latn", "en", self.root / "hidden.html", provenance=restricted)
        with self.assertRaises(glyph.ValidationError):
            glyph.import_font(self.root / "missing.otf", self.root / "hidden-font", provenance=restricted, text="A")
        self.assertFalse((self.root / "hidden.html").exists())
        self.assertFalse((self.root / "hidden-font").exists())
        existing = self.root / "existing"
        existing.mkdir()
        (existing / "keep").write_text("user work")
        with self.assertRaises(glyph.ValidationError):
            glyph.import_capture(self.write_manifest(), existing)
        self.assertEqual((existing / "keep").read_text(), "user work")

    def test_source_verification_and_capture_cli_bind_actual_export(self):
        repo, db, provenance = self.source_export()
        self.assertEqual(glyph.verify_source(provenance, repo, db), provenance)
        manifest = {**self.manifest, **provenance}
        output = self.root / "verified-cli-capture"
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = glyph.main(["import-capture", str(self.write_manifest(manifest)), str(output),
                                 "--repo", str(repo), "--db", str(db)])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["source"], provenance["source"])
        self.assertTrue((output / "preview.html").exists())

    def test_actual_reserve_withheld_and_stale_hash_block_every_derivative_cli(self):
        repo, db, provenance = self.source_export()
        provenance_path = self.root / "provenance.json"
        text_path = self.root / "source.txt"
        text_path.write_text("A")
        font = self.root / "fixture.otf"
        font.write_bytes(build("Fixture Source", "none"))
        policy_path = db / "release/p001.json"
        cases = [
            ("reserve", {"pool": "reserve", "publicStatus": "private"}),
            ("withheld", {"pool": "unsorted", "publicStatus": "withheld"}),
            ("stale", {"pool": "unsorted", "publicStatus": "private"}),
        ]
        for case, policy in cases:
            policy_path.write_text(json.dumps(policy))
            declared = copy.deepcopy(provenance)  # Always declares private/unsorted.
            if case == "stale":
                declared["source"]["sha256"] = "f" * 64
            provenance_path.write_text(json.dumps(declared))
            manifest_path = self.write_manifest({**self.manifest, **declared})
            for command in ("sheet", "import-font", "import-capture"):
                with self.subTest(case=case, command=command):
                    output = self.root / (case + "-" + command) / "output"
                    args = [command]
                    if command == "import-capture":
                        args += [str(manifest_path), str(output)]
                    else:
                        if command == "import-font":
                            args += [str(font)]
                        args += [str(output), "--provenance", str(provenance_path),
                                 "--text-file", str(text_path), "--language", "en", "--script", "Latn"]
                    args += ["--repo", str(repo), "--db", str(db)]
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                        glyph.main(args)
                    self.assertEqual(error.exception.code, 2)
                    self.assertFalse(output.parent.exists())

    def test_policy_mismatch_exported_correction_and_missing_db_are_not_inferred(self):
        repo, db, provenance = self.source_export()
        mismatch = copy.deepcopy(provenance)
        mismatch["source"].update(collection="series", visibility="public")
        with self.assertRaisesRegex(glyph.ValidationError, "canonical export policy"):
            glyph.verify_source(mismatch, repo, db)
        (db / "reviews/line1.json").write_text(json.dumps({"status": "corrected", "original": "A", "text": "B"}))
        with self.assertRaisesRegex(glyph.ValidationError, "fingerprint"):
            glyph.verify_source(provenance, repo, db)
        with self.assertRaisesRegex(glyph.ValidationError, "explicit studio export"):
            glyph.verify_source(provenance, repo, None)
        for command in ("sheet", "import-font", "import-capture"):
            args = [command]
            if command == "import-capture":
                args += [str(self.write_manifest()), str(self.root / "no-db")]
            else:
                if command == "import-font":
                    args += ["unused.otf"]
                args += [str(self.root / "no-db"), "--text-file", "unused.txt",
                         "--provenance", "unused.json", "--language", "en", "--script", "Latn"]
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                glyph.main(args)
            self.assertEqual(error.exception.code, 2)
            self.assertFalse((self.root / "no-db").exists())


if __name__ == "__main__":
    unittest.main()
