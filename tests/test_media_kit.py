"""Private media exports: source selection, honest QA and complete byte coverage."""

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


kit = module("media_kit", "production/kit/kit.py")
checker = module("media_check", "production/tools/check_substitution.py")


def config(pid):
    path = REPO / "production/kit/config" / f"{pid}.json"
    value = json.loads(path.read_text())
    value.update(_config_name=path.name, _config_path=str(path), _no_ocr=True)
    return value


class MediaKitTests(unittest.TestCase):
    def test_source_hash_and_version_membership_fail_closed(self):
        cfg = config("p004")
        cfg["source_inputs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source hash mismatch"):
            kit.SourcePackage(REPO, cfg)
        cfg = config("p004")
        cfg["cover_block"] = 0
        with self.assertRaisesRegex(ValueError, "outside the selected version"):
            kit.SourcePackage(REPO, cfg)
        cfg = config("p001")
        cfg["later_version"]["blocks"] = [0, 1, 2, 3]
        with self.assertRaisesRegex(ValueError, "later blocks"):
            kit.SourcePackage(REPO, cfg).later_source()

    def test_later_source_and_unknown_geometry_are_its_own(self):
        src = kit.SourcePackage(REPO, config("p001"))
        later = src.later_source()
        self.assertEqual(later.page["id"], "diary62a")
        self.assertEqual(later.version_blocks(), [0, 1, 2])
        geometry = later.geometry([0, 1, 2])
        self.assertEqual(geometry["expected_lines"], 16)
        self.assertEqual(geometry["measured_lines"], 13)
        self.assertEqual(geometry["missing_line_geometry"], [[0, 3], [1, 0], [2, 5]])
        self.assertFalse(geometry["geometry_complete"])
        crop = later.selection_box([0, 1, 2])
        neighbour_top = min(row[3] for row in later.page["x"] if row[0] in (3, 4))
        self.assertLessEqual(crop[3], neighbour_top)
        _, sources = kit.output_provenance(src, "carousel/carousel-05-version.jpg")
        self.assertEqual(sources[0]["version_id"], "p001-diary62a-0")
        self.assertEqual(sources[0]["source"], "production/assets/diary62a.jpg")
        self.assertNotIn("diary1", {s["page_id"] for s in sources})

    def test_page_and_widget_pixels_exclude_other_p004_drafts(self):
        src = kit.SourcePackage(REPO, config("p004"))
        # Fixture bands stand in for the neighbouring draft regions. The actual
        # source geometry selects only the middle band, so neither colour may
        # survive in page or widget consumer output.
        src.image = Image.new("RGB", src.image.size, (20, 20, 20))
        draw = ImageDraw.Draw(src.image)
        upper_end = max(r[5] for r in src.page["x"] if r[0] == 0)
        lower_start = min(r[3] for r in src.page["x"] if r[0] == 2)
        draw.rectangle((0, 0, src.src_w, round(src.src_h * upper_end)), fill=(255, 0, 0))
        draw.rectangle((0, round(src.src_h * lower_start), src.src_w, src.src_h), fill=(0, 0, 255))
        rendered = kit.render_page(src, None)
        pixels = rendered.tobytes()
        self.assertNotIn(bytes((255, 0, 0)) * 3, pixels)
        self.assertNotIn(bytes((0, 0, 255)) * 3, pixels)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            widget = kit.make_widget_kit(src, out, src.cfg)
            for rel, _, _ in widget["tiles"]:
                with Image.open(out / rel) as im:
                    pixels = im.convert("RGB").tobytes()
                # No saturated red/blue neighbour survives lossy encoding.
                self.assertFalse(any((r > 200 and g < 50 and b < 50) or
                                     (b > 200 and g < 50 and r < 50)
                                     for r, g, b in zip(pixels[0::3], pixels[1::3], pixels[2::3])))
                _, sources = kit.output_provenance(src, rel)
                self.assertEqual(sources[0]["blocks"], [1])

    def test_qa_later_lines_missing_geometry_and_ocr_skip(self):
        src = kit.SourcePackage(REPO, config("p001"))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stills = kit.render_still_set(src, out, None, src.cfg)
            with patch.object(kit, "ensure_vision_ocr", side_effect=AssertionError("OCR disabled")):
                qa = kit.run_qa(src, out, stills, src.cfg)
            target = qa["targets"]["carousel-05-version"]
            self.assertEqual(target["expected_lines"], 16)
            self.assertEqual(target["lines"], 13)
            self.assertEqual(target["selection"]["page_id"], "diary62a")
            self.assertIsNone(target["geometry_readable_at_390"])
            self.assertEqual(target["ocr_status"], "skipped")
            self.assertEqual(qa["ocr"]["status"], "skipped")
            self.assertNotIn("ocr_word_recall", target)

    def test_manifest_covers_every_output_and_rejects_tampering(self):
        src = kit.SourcePackage(REPO, config("p004"))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stills = kit.render_still_set(src, out, None, src.cfg)
            widget = kit.make_widget_kit(src, out, src.cfg)
            qa = kit.run_qa(src, out, stills, src.cfg)
            manifest = kit.build_manifest(src, out, src.cfg, stills, {}, {}, widget, qa, REPO)
            self.assertEqual(checker.verify_export(out, manifest), [])
            self.assertFalse(manifest["clearance"]["may_publish"])
            self.assertIn("MANIFEST.md", {e["path"] for e in manifest["assets"]})
            self.assertNotIn("manifest.json", {e["path"] for e in manifest["assets"]})
            (out / "untracked.txt").write_text("extra output")
            self.assertTrue(any("coverage mismatch" in e for e in checker.verify_export(out, manifest)))
            (out / "untracked.txt").unlink()
            first = out / manifest["assets"][0]["path"]
            first.write_bytes(first.read_bytes() + b"tampered")
            self.assertTrue(any("output bytes differ" in e for e in checker.verify_export(out, manifest)))
            corrupt = copy.deepcopy(manifest)
            corrupt["assets"][0]["sources"][0]["blocks"] = [0]
            self.assertTrue(any("wrong piece/version/blocks" in e for e in checker.verify_export(out, corrupt)))
            corrupt = copy.deepcopy(manifest)
            declared_identity = next(e for e in manifest["source_inputs"] if "identity chip" in e["role"])
            corrupt["assets"][0]["sources"][0].update(
                source=declared_identity["path"], source_sha256=declared_identity["sha256"])
            self.assertTrue(any("wrong piece/version/blocks" in e for e in checker.verify_export(out, corrupt)))
            corrupt = copy.deepcopy(manifest)
            corrupt["assets"][0].update(role="reel", fps=30, duration_seconds=6)
            self.assertTrue(any("incomplete encoder frame sequence" in e for e in checker.verify_export(out, corrupt)))

    def test_reel_frame_sources_follow_holds_and_transitions(self):
        src = kit.SourcePackage(REPO, config("p001"))
        for index, expected in ((0, {"diary1"}), (30, {"diary1", "diary62a"}),
                                (60, {"diary62a"}), (150, {"diary1"})):
            _, sources = kit.output_provenance(src, f"reel/_frames/f{index:04d}.png")
            self.assertEqual({s["page_id"] for s in sources}, expected)

    def test_accepted_readings_override_raw_lines_without_rewriting_them(self):
        later = kit.SourcePackage(REPO, config("p001")).later_source()
        before = copy.deepcopy(later.page["B"])
        expected = [later.j.get("acceptedReadings", {}).get(f"diary62a-{b}-{i}", raw)
                    for b in later.version_blocks() for i, raw in enumerate(later.page["B"][b]["L"])]
        self.assertEqual(later.text(later.version_blocks()), expected)
        self.assertNotEqual(expected, [line for b in later.version_blocks() for line in later.page["B"][b]["L"]])
        self.assertEqual(later.page["B"], before)

    def test_accepted_readings_follow_explicit_line_ids_before_legacy_ids(self):
        src = kit.SourcePackage(REPO, config("p004"))
        src.page["B"][1]["lineIds"] = [f"supplied-line-{i}" for i in range(9)]
        src.j["acceptedReadings"] = {"supplied-line-0": "TECHNICAL ACCEPTED READING",
                                      "diary3-1-0": "STALE LEGACY TEST KEY"}
        self.assertEqual(src.text([1])[0], "TECHNICAL ACCEPTED READING")
        self.assertEqual(src.text([1])[1:], src.page["B"][1]["L"][1:])

    def test_each_manifest_selection_binds_its_own_v2_logical_source(self):
        src = kit.SourcePackage(REPO, config("p001"))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stills = kit.render_still_set(src, out, None, src.cfg)
            widget = kit.make_widget_kit(src, out, src.cfg)
            qa = kit.run_qa(src, out, stills, src.cfg)
            manifest = kit.build_manifest(src, out, src.cfg, stills, {}, {}, widget, qa, REPO)
            expected = [kit.source_binding(kit.source_snapshot(REPO, "p001", vid))
                        for vid in ("p001-diary1-0", "p001-diary62a-0")]
            self.assertEqual(manifest["source_bindings"], expected)
            self.assertEqual(checker.verify_export(out, manifest), [])
            later = next(e for e in manifest["assets"] if e["path"] == "carousel/carousel-05-version.jpg")
            self.assertEqual(later["sources"][0]["source_binding"], expected[1])
            later["sources"][0]["source_binding"] = expected[0]
            self.assertTrue(any("logical source selection differs" in e for e in checker.verify_export(out, manifest)))


if __name__ == "__main__":
    unittest.main()
